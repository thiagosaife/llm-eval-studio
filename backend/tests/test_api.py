"""End-to-end checks of the API contract the frontend depends on."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_list_metrics_shape():
    resp = client.get("/api/metrics")
    assert resp.status_code == 200
    metrics = resp.json()
    ids = {m["id"] for m in metrics}
    assert {"exact_match", "rouge1", "rouge2", "rougeL"} <= ids
    for m in metrics:
        # the fields the picker + teaching notes rely on
        assert set(m) >= {
            "id", "name", "family", "description",
            "requires_reference", "range", "how_to_read", "caveat",
        }


def test_evaluate_full_loop():
    resp = client.post(
        "/api/evaluate",
        json={
            "metrics": ["exact_match", "rouge1", "rougeL"],
            "dataset_name": "smoke",
            "cases": [
                {"id": "c1", "input": "Capital of France?",
                 "prediction": "Paris", "reference": "paris"},
                {"id": "c2", "input": "Summarize.",
                 "prediction": "the cat ran", "reference": "the dog ran"},
            ],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["run_id"].startswith("run-")
    assert len(body["per_case"]) == 2
    # c1 is an exact match after normalization
    assert body["per_case"][0]["scores"]["exact_match"] == 1.0
    # aggregate exact_match = mean(1.0, 0.0) = 0.5
    assert body["aggregate"]["exact_match"] == 0.5
    # run is retrievable afterwards
    got = client.get(f"/api/runs/{body['run_id']}")
    assert got.status_code == 200
    assert got.json()["run_id"] == body["run_id"]


def test_reference_metric_skipped_when_no_reference():
    resp = client.post(
        "/api/evaluate",
        json={
            "metrics": ["exact_match"],
            "cases": [{"id": "c1", "prediction": "anything", "reference": None}],
        },
    )
    body = resp.json()
    # not applicable -> null, and excluded from the aggregate (-> null)
    assert body["per_case"][0]["scores"]["exact_match"] is None
    assert body["aggregate"]["exact_match"] is None


def test_unknown_metric_rejected():
    resp = client.post(
        "/api/evaluate",
        json={"metrics": ["does_not_exist"],
              "cases": [{"id": "c1", "prediction": "x", "reference": "x"}]},
    )
    assert resp.status_code == 400


def test_missing_run_is_404():
    assert client.get("/api/runs/nope").status_code == 404


def test_metrics_include_phase2_with_flags():
    metrics = client.get("/api/metrics").json()
    by = {m["id"]: m for m in metrics}
    assert {"accuracy", "precision", "recall", "f1", "cosine", "bertscore"} <= set(by)
    # set-level metrics are flagged aggregate_only
    assert by["precision"]["aggregate_only"] is True
    assert by["accuracy"]["aggregate_only"] is False
    # every metric advertises availability (embedding libs are installed here)
    assert all(isinstance(m["available"], bool) for m in metrics)
    assert by["accuracy"]["available"] is True


def test_classification_run_and_confusion_matrix():
    cases = [
        {"id": "1", "prediction": "pos", "reference": "pos"},
        {"id": "2", "prediction": "neg", "reference": "pos"},
        {"id": "3", "prediction": "neg", "reference": "neg"},
        {"id": "4", "prediction": "neg", "reference": "neg"},
    ]
    resp = client.post(
        "/api/evaluate",
        json={"metrics": ["accuracy", "precision", "recall", "f1"], "cases": cases},
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["aggregate"]["accuracy"] == 0.75
    assert body["aggregate"]["precision"] is not None
    # accuracy has a per-case value; set-level precision does not
    assert body["per_case"][0]["scores"]["accuracy"] == 1.0
    assert body["per_case"][0]["scores"]["precision"] is None

    cm = body["confusion_matrix"]
    assert cm["labels"] == ["neg", "pos"]
    # matrix[true][pred]: true=neg -> 2 correct; true=pos -> 1 right, 1 called neg
    assert cm["matrix"] == [[2, 0], [1, 1]]


def test_no_confusion_matrix_without_classification_metric():
    resp = client.post(
        "/api/evaluate",
        json={"metrics": ["rouge1"], "cases": [{"id": "1", "prediction": "a", "reference": "a"}]},
    )
    assert resp.json()["confusion_matrix"] is None
