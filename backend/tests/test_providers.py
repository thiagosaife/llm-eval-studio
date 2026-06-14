"""Provider registry: model routing, pricing, key resolution, token counting.

No network: generation paths aren't exercised here (the api tests mock those).
We verify the routing/pricing/key logic and OpenAI's *offline* tiktoken count.
"""
import importlib.util

import pytest

from app import llm, providers
from app.providers.openai_provider import OpenAIProvider


def test_provider_for_model_routes_by_id():
    assert providers.provider_for_model("claude-opus-4-8").id == "anthropic"
    assert providers.provider_for_model("gpt-5.1").id == "openai"
    assert providers.provider_for_model("gemini-2.5-flash").id == "gemini"


def test_unknown_model_falls_back_to_default_provider():
    # A stray/legacy id still resolves (to the default's provider) rather than crash.
    assert providers.provider_for_model("totally-made-up").id == "anthropic"


def test_all_models_span_every_provider():
    by_provider = {pid for _, _, pid in providers.all_models()}
    assert {"anthropic", "openai", "gemini"} <= by_provider


def test_cost_uses_each_providers_pricing():
    # opus 4.8 = $5/$25 → 1M+1M = $30
    assert llm.cost("claude-opus-4-8", 1_000_000, 1_000_000) == 30.0
    # gpt-4o-mini = $0.15/$0.60 → $0.75
    assert llm.cost("gpt-4o-mini", 1_000_000, 1_000_000) == 0.75
    # gemini-2.0-flash = $0.10/$0.40 → $0.50
    assert llm.cost("gemini-2.0-flash", 1_000_000, 1_000_000) == 0.5


def test_heuristic_estimate_is_provider_agnostic_and_positive():
    short = llm.estimate_input_tokens("", "hi")
    long = llm.estimate_input_tokens("", "hi" * 1000)
    assert 0 < short < long


def test_key_for_picks_the_models_provider_key():
    keys = {"openai": "sk-openai", "anthropic": "sk-anthropic"}
    assert llm.key_for("gpt-5.1", keys) == "sk-openai"
    assert llm.key_for("claude-opus-4-8", keys) == "sk-anthropic"
    # no key for the model's provider → None (env is the fallback, resolved later)
    assert llm.key_for("gemini-2.5-pro", keys) is None
    assert llm.key_for("gpt-5.1", None) is None


def test_request_key_overrides_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "env-key")
    prov = OpenAIProvider()
    assert prov.resolve_key("request-key") == "request-key"  # request wins
    assert prov.resolve_key(None) == "env-key"  # env is the fallback
    assert prov.resolve_key("   ") == "env-key"  # blank request key ignored


def test_available_requires_sdk_and_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    prov = OpenAIProvider()
    assert prov.available(None) is False  # no key
    # with a key, availability tracks whether the SDK is importable
    assert prov.available("sk-x") is prov.sdk_installed()


@pytest.mark.skipif(
    importlib.util.find_spec("tiktoken") is None, reason="tiktoken not installed"
)
def test_openai_count_input_tokens_offline():
    # tiktoken runs locally (no key) and should give a sane positive count.
    n = OpenAIProvider().count_input_tokens("gpt-4o", "You are a judge.", "Grade this answer.")
    assert n > 0
