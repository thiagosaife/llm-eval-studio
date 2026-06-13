"""Unit tests for the defensive judge-output parser (no network)."""
from app.llm import _cost, _parse_judgment


def test_parse_judgment_1_to_5_scale():
    score, rationale = _parse_judgment('{"score": 4, "rationale": "Mostly correct."}')
    assert score == 0.8
    assert rationale == "Mostly correct."


def test_parse_judgment_already_0_1():
    score, _ = _parse_judgment('{"score": 0.5, "rationale": "ok"}')
    assert score == 0.5


def test_parse_judgment_clamps_and_tolerates_prose():
    score, rationale = _parse_judgment(
        'Here is my grade:\n{"score": 5, "rationale": "Excellent answer."}\nThanks!'
    )
    assert score == 1.0
    assert rationale == "Excellent answer."


def test_parse_judgment_unparseable_returns_none():
    score, rationale = _parse_judgment("I could not produce JSON.")
    assert score is None
    assert rationale == "I could not produce JSON."


def test_cost_uses_pricing_table():
    # opus 4.8 = $5/1M in, $25/1M out → 1M in + 1M out = $30
    assert _cost("claude-opus-4-8", 1_000_000, 1_000_000) == 30.0
