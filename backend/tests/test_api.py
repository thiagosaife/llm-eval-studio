"""End-to-end checks of the API contract the frontend depends on."""
from fastapi.testclient import TestClient

from app import llm
from app.llm import Completion
from app.main import app
from app.metrics import registry

client = TestClient(app)


def _fake_completion(text: str) -> Completion:
    return Completion(
        text=text, model="claude-opus-4-8", latency_ms=123.4, tokens_in=50, tokens_out=10, cost=0.001
    )


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


# --- Phase 3: LLM-judge, RAG, live generation, operational ------------------


def test_phase3_metrics_listed_with_flags():
    by = {m["id"]: m for m in client.get("/api/metrics").json()}
    assert {"llm_judge", "faithfulness", "answer_relevancy", "context_relevancy"} <= set(by)
    assert by["llm_judge"]["family"] == "model_judge"
    assert by["llm_judge"]["produces_rationale"] is True
    assert by["faithfulness"]["family"] == "rag"
    assert by["faithfulness"]["requires_context"] is True


def test_models_endpoint():
    models = client.get("/api/models").json()
    # spans every provider, each model tagged with its provider
    assert any(m["id"] == "claude-opus-4-8" and m["provider"] == "anthropic" for m in models)
    assert any(m["provider"] == "openai" for m in models)
    assert any(m["provider"] == "gemini" for m in models)


def test_providers_endpoint():
    providers = {p["id"]: p for p in client.get("/api/providers").json()}
    assert {"anthropic", "openai", "gemini"} <= set(providers)
    anthropic = providers["anthropic"]
    assert set(anthropic) >= {"id", "name", "env_var", "env_available", "sdk_installed", "models"}
    assert anthropic["env_var"] == "ANTHROPIC_API_KEY"
    assert any(m["id"] == "claude-opus-4-8" for m in anthropic["models"])
    assert providers["openai"]["env_var"] == "OPENAI_API_KEY"
    assert providers["gemini"]["env_var"] == "GEMINI_API_KEY"


def test_unavailable_llm_metric_rejected_without_key(monkeypatch):
    # No usable key for the judge model's provider → the run is rejected.
    monkeypatch.setattr(llm, "available", lambda *a, **k: False)
    resp = client.post(
        "/api/evaluate",
        json={"metrics": ["llm_judge"], "cases": [{"id": "1", "prediction": "x"}]},
    )
    assert resp.status_code == 400
    assert "unavailable" in resp.json()["detail"].lower()


def test_llm_judge_via_mocked_provider(monkeypatch):
    monkeypatch.setattr(llm, "available", lambda *a, **k: True)
    monkeypatch.setattr(
        llm, "complete", lambda *a, **k: _fake_completion('{"score": 4, "rationale": "Solid."}')
    )
    resp = client.post(
        "/api/evaluate",
        json={
            "metrics": ["llm_judge"],
            "judge": {"rubric": "Rate correctness."},
            "cases": [{"id": "1", "input": "Capital of France?", "prediction": "Paris"}],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["per_case"][0]["scores"]["llm_judge"] == 0.8  # 4/5
    assert body["per_case"][0]["rationales"]["llm_judge"] == "Solid."
    # judge calls cost money/time → operational summary is attached
    assert body["operational"]["calls"] == 1
    assert body["operational"]["latency_p50_ms"] == 123.4


def test_generate_via_mocked_provider(monkeypatch):
    monkeypatch.setattr(llm, "available", lambda *a, **k: True)
    monkeypatch.setattr(llm, "complete", lambda *a, **k: _fake_completion("Paris"))
    resp = client.post(
        "/api/generate",
        json={"cases": [{"id": "1", "input": "Capital of France?"}], "model": "claude-opus-4-8"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["cases"][0]["prediction"] == "Paris"
    assert body["cases"][0]["operational"]["tokens_out"] == 10
    assert body["summary"]["calls"] == 1


def test_generate_with_openai_model_routes_to_its_provider(monkeypatch):
    # Selecting a GPT model + supplying an OpenAI key (via the request) runs it;
    # the model id alone tells the backend which provider to use.
    seen = {}

    def fake_complete(prompt, model=None, system=None, max_tokens=1024, api_key=None):
        seen["model"] = model
        seen["api_key"] = api_key
        return _fake_completion("Madrid")

    monkeypatch.setattr(llm, "available", lambda *a, **k: True)
    monkeypatch.setattr(llm, "complete", fake_complete)
    resp = client.post(
        "/api/generate",
        json={
            "cases": [{"id": "1", "input": "Capital of Spain?"}],
            "model": "gpt-5.1",
            "keys": {"openai": "sk-test"},
        },
    )
    assert resp.status_code == 200
    assert resp.json()["cases"][0]["prediction"] == "Madrid"
    assert seen["model"] == "gpt-5.1"
    assert seen["api_key"] == "sk-test"  # request key threaded to the provider


def test_generate_rejected_without_key(monkeypatch):
    monkeypatch.setattr(llm, "available", lambda *a, **k: False)
    resp = client.post("/api/generate", json={"cases": [{"id": "1", "input": "hi"}]})
    assert resp.status_code == 400


def test_runs_list_returns_summaries():
    client.post(
        "/api/evaluate",
        json={"metrics": ["rouge1"], "cases": [{"id": "1", "prediction": "a", "reference": "a"}]},
    )
    runs = client.get("/api/runs").json()
    assert isinstance(runs, list) and len(runs) >= 1
    assert {"run_id", "created_at", "metrics", "aggregate"} <= set(runs[0])
