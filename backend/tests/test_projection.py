"""Tests for the dimensionality-reduction explorer (/api/projection*, /api/project).

Follows the no-model-download rule: the `sample` source uses iris (tiny, ships
with scikit-learn), and the `dataset` source monkeypatches the embedder so we
never load the sentence-transformers model (mirrors how test_llm mocks Claude).
"""
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app import embeddings_util, projection
from app.main import app

client = TestClient(app)


# --- the engine itself ------------------------------------------------------


def test_pca_reduce_shape_determinism_and_variance():
    rng = np.random.default_rng(0)
    vectors = rng.normal(size=(40, 16))
    coords_a, meta = projection.reduce(vectors, "pca", {})
    coords_b, _ = projection.reduce(vectors, "pca", {})
    assert coords_a.shape == (40, 2)
    assert np.allclose(coords_a, coords_b)  # deterministic
    assert len(meta["variance_explained"]) == 2
    assert all(0.0 <= v <= 1.0 for v in meta["variance_explained"])


def test_tsne_clamps_perplexity_to_sample_size():
    rng = np.random.default_rng(0)
    vectors = rng.normal(size=(6, 8))  # tiny: perplexity must drop below n
    coords, meta = projection.reduce(vectors, "tsne", {"perplexity": 30})
    assert coords.shape == (6, 2)
    assert meta["perplexity"] < 6


# --- catalog endpoints ------------------------------------------------------


def test_list_algorithms_shape():
    resp = client.get("/api/projection/algorithms")
    assert resp.status_code == 200
    algos = {a["id"]: a for a in resp.json()}
    assert {"pca", "tsne", "umap"} <= set(algos)
    # pca/tsne ship with scikit-learn, so they're always available here
    assert algos["pca"]["available"] is True
    assert algos["tsne"]["available"] is True
    # params drive the UI sliders
    assert algos["tsne"]["params"][0]["key"] == "perplexity"


def test_list_samples_shape():
    resp = client.get("/api/projection/samples")
    assert resp.status_code == 200
    samples = {s["id"]: s for s in resp.json()}
    assert {"digits", "iris"} <= set(samples)
    assert samples["iris"]["n_features"] == 4


# --- /api/project: sample source -------------------------------------------


def test_project_sample_iris_pca_and_tsne():
    resp = client.post(
        "/api/project",
        json={"source": "sample", "sample_id": "iris", "algorithms": ["pca", "tsne"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["n_points"] == 150
    assert body["dims_in"] == 4
    assert body["label_kind"] == "category"
    by_algo = {r["algorithm"]: r for r in body["results"]}
    assert set(by_algo) == {"pca", "tsne"}
    assert len(by_algo["pca"]["points"]) == 150
    assert by_algo["pca"]["meta"]["variance_explained"] is not None
    assert by_algo["tsne"]["meta"]["perplexity"] is not None
    # iris labels (species) come through for coloring
    assert by_algo["pca"]["points"][0]["label"] in {"setosa", "versicolor", "virginica"}


def test_project_unknown_sample_400():
    resp = client.post(
        "/api/project", json={"source": "sample", "sample_id": "nope", "algorithms": ["pca"]}
    )
    assert resp.status_code == 400


# --- /api/project: dataset source (embedder monkeypatched) ------------------


def _fake_embed(texts):
    """Deterministic synthetic embeddings — no model download."""
    rng = np.random.default_rng(len(texts))
    return rng.normal(size=(len(texts), 8))


def test_project_dataset_categorical_labels(monkeypatch):
    monkeypatch.setattr(embeddings_util, "available", lambda: True)
    monkeypatch.setattr(embeddings_util, "embed_texts", _fake_embed)
    cases = [
        {"id": "c1", "prediction": "love it", "reference": "positive"},
        {"id": "c2", "prediction": "terrible", "reference": "negative"},
        {"id": "c3", "prediction": "great stuff", "reference": "positive"},
        {"id": "c4", "prediction": "awful", "reference": "negative"},
    ]
    resp = client.post(
        "/api/project",
        json={"source": "dataset", "field": "prediction", "algorithms": ["pca"], "cases": cases},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["n_points"] == 4
    assert body["label_kind"] == "category"  # short, repeated references
    pts = body["results"][0]["points"]
    assert {p["label"] for p in pts} == {"positive", "negative"}
    assert pts[0]["text"] == "love it"  # preview of the embedded field


def test_project_dataset_free_text_has_no_labels(monkeypatch):
    monkeypatch.setattr(embeddings_util, "available", lambda: True)
    monkeypatch.setattr(embeddings_util, "embed_texts", _fake_embed)
    cases = [
        {"id": "c1", "prediction": "a", "reference": "a long unique gold answer number one here"},
        {"id": "c2", "prediction": "b", "reference": "another entirely different long gold answer"},
        {"id": "c3", "prediction": "c", "reference": "yet a third distinct lengthy reference text"},
    ]
    resp = client.post(
        "/api/project",
        json={"source": "dataset", "field": "prediction", "algorithms": ["pca"], "cases": cases},
    )
    assert resp.status_code == 200
    assert resp.json()["label_kind"] == "none"


def test_project_dataset_too_few_cases_400(monkeypatch):
    monkeypatch.setattr(embeddings_util, "available", lambda: True)
    monkeypatch.setattr(embeddings_util, "embed_texts", _fake_embed)
    resp = client.post(
        "/api/project",
        json={
            "source": "dataset",
            "field": "prediction",
            "algorithms": ["pca"],
            "cases": [{"id": "c1", "prediction": "only one"}],
        },
    )
    assert resp.status_code == 400


# --- shared validation ------------------------------------------------------


def test_project_unknown_algorithm_400():
    resp = client.post(
        "/api/project", json={"source": "sample", "sample_id": "iris", "algorithms": ["bogus"]}
    )
    assert resp.status_code == 400


def test_project_no_algorithms_400():
    resp = client.post("/api/project", json={"source": "sample", "sample_id": "iris", "algorithms": []})
    assert resp.status_code == 400


def test_project_umap_when_available():
    if not projection.is_available("umap"):
        pytest.skip("umap-learn not installed")
    resp = client.post(
        "/api/project",
        json={
            "source": "sample",
            "sample_id": "iris",
            "algorithms": ["umap"],
            "params": {"umap": {"n_neighbors": 10, "min_dist": 0.2}},
        },
    )
    assert resp.status_code == 200
    meta = resp.json()["results"][0]["meta"]
    assert meta["n_neighbors"] == 10
    assert meta["min_dist"] == 0.2
