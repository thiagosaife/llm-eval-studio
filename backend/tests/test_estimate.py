"""Pre-run cost estimator: token projection + cost (heuristic and exact paths)."""
from fastapi.testclient import TestClient

from app import llm
from app.llm import estimate_input_tokens
from app.main import app

client = TestClient(app)


def test_estimate_input_tokens_positive_and_scales():
    short = estimate_input_tokens("", "hi")
    long = estimate_input_tokens("", "hi" * 1000)
    assert short > 0
    assert long > short


def test_estimate_heuristic_needs_no_key():
    resp = client.post(
        "/api/estimate",
        json={
            "metrics": ["llm_judge"],
            "cases": [
                {"id": "1", "input": "Capital of France?", "prediction": "Paris"},
                {"id": "2", "input": "Capital of Spain?", "prediction": "Madrid"},
            ],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["llm_calls"] == 2
    assert body["tokens_in"] > 0
    assert body["exact"] is False
    assert body["expected_tokens_out"] == 2 * llm.JUDGE_OUTPUT_TOKENS_EST
    assert body["max_tokens_out"] == 2 * llm.JUDGE_MAX_TOKENS
    # worst case (1024-token replies) costs strictly more than expected (~80).
    assert body["expected_cost"] < body["max_cost"]
    assert body["per_metric"][0]["metric_id"] == "llm_judge"
    assert body["per_metric"][0]["calls"] == 2


def test_estimate_skips_inapplicable_cases():
    # llm_judge needs a prediction; the second case has none → only 1 call.
    resp = client.post(
        "/api/estimate",
        json={
            "metrics": ["llm_judge"],
            "cases": [
                {"id": "1", "prediction": "Paris"},
                {"id": "2", "input": "no prediction here"},
            ],
        },
    )
    assert resp.json()["llm_calls"] == 1


def test_estimate_non_llm_metrics_are_free():
    resp = client.post(
        "/api/estimate",
        json={
            "metrics": ["exact_match", "rouge1"],
            "cases": [{"id": "1", "prediction": "a", "reference": "a"}],
        },
    )
    body = resp.json()
    assert body["llm_calls"] == 0
    assert body["expected_cost"] == 0
    assert body["max_cost"] == 0
    assert body["exact"] is False
    assert body["per_metric"] == []


def test_estimate_exact_path_uses_count_tokens(monkeypatch):
    monkeypatch.setattr(llm, "available", lambda: True)
    monkeypatch.setattr(llm, "count_input_tokens", lambda model, system, prompt: 100)
    resp = client.post(
        "/api/estimate",
        json={
            "metrics": ["llm_judge"],
            "exact": True,
            "cases": [{"id": "1", "input": "Q", "prediction": "A"}],
        },
    )
    body = resp.json()
    assert body["exact"] is True
    assert body["tokens_in"] == 100
    assert body["expected_cost"] == llm.cost(
        "claude-opus-4-8", 100, llm.JUDGE_OUTPUT_TOKENS_EST
    )


def test_estimate_exact_falls_back_on_provider_error(monkeypatch):
    monkeypatch.setattr(llm, "available", lambda: True)

    def boom(*a, **k):
        raise RuntimeError("no creds")

    monkeypatch.setattr(llm, "count_input_tokens", boom)
    resp = client.post(
        "/api/estimate",
        json={
            "metrics": ["llm_judge"],
            "exact": True,
            "cases": [{"id": "1", "input": "Q", "prediction": "A"}],
        },
    )
    body = resp.json()
    assert body["exact"] is False  # downgraded to the heuristic
    assert body["tokens_in"] > 0


def test_estimate_unknown_metric_rejected():
    resp = client.post(
        "/api/estimate",
        json={"metrics": ["nope"], "cases": [{"id": "1", "prediction": "x"}]},
    )
    assert resp.status_code == 400


def test_metrics_expose_estimable_flag():
    by = {m["id"]: m for m in client.get("/api/metrics").json()}
    # the anthropic SDK is installed in the test env → llm metrics are estimable
    # (selectable for an estimate) even if no key makes them runnable.
    assert by["llm_judge"]["estimable"] is True
    assert by["exact_match"]["estimable"] is True
