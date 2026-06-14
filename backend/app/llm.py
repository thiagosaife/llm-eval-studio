"""The backend's LLM facade (doc §5.2, Phase 3).

Historically this module *was* the Anthropic integration. It is now a thin,
provider-aware facade over `app/providers/` so the rest of the app — `api.py`,
the judge metric, the cost estimator, the tests — keeps calling `llm.complete`,
`llm.judge`, `llm.cost`, `llm.available`, etc. without caring which vendor a
model belongs to. Routing is by *model id*: `providers.provider_for_model(model)`
picks Anthropic / OpenAI / Gemini.

Keys: a request may carry a per-provider key (the UI's "bring your own key"); it
wins over the environment. `key_for(model, keys)` resolves the right one.

Everything stays lazy: SDK clients are created on first use, and a provider whose
SDK or key is missing reports `available()` False so the UI greys it out rather
than failing a run.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from . import providers
from .providers import Completion, DEFAULT_MODEL, provider_for_model
from .providers.base import heuristic_input_tokens

# Output cap per judge call, and the expected output size used for cost estimates.
# A judge reply is a tiny `{"score", "rationale"}` JSON — far below the cap — so
# the estimator reports both an expected cost (~JUDGE_OUTPUT_TOKENS_EST) and a
# guaranteed worst-case ceiling (JUDGE_MAX_TOKENS).
JUDGE_MAX_TOKENS = 1024
JUDGE_OUTPUT_TOKENS_EST = 80


# --- key resolution ---------------------------------------------------------


def key_for(model: str, keys: Optional[Dict[str, str]]) -> Optional[str]:
    """The request-supplied key for a model's provider, if any (env is the fallback,
    resolved inside the provider). `keys` is a provider_id -> key map from the UI."""
    if not keys:
        return None
    provider = provider_for_model(model)
    value = keys.get(provider.id)
    return value.strip() if value and value.strip() else None


# --- availability -----------------------------------------------------------


def sdk_installed(model: Optional[str] = None) -> bool:
    """SDK importable? For a specific model, that provider's SDK; otherwise any."""
    if model is None:
        return providers.any_sdk()
    return provider_for_model(model).sdk_installed()


def available(model: Optional[str] = None, api_key: Optional[str] = None) -> bool:
    """Runnable now? For a specific model, that provider has SDK + a usable key
    (request key or env); with no model, true if ANY provider is available."""
    if model is None:
        return providers.any_available()
    return provider_for_model(model).available(api_key)


def unavailable_reason(model: Optional[str] = None) -> str:
    if model is None:
        return "Add an API key for at least one provider to enable LLM features."
    return provider_for_model(model).unavailable_reason()


# --- pricing ----------------------------------------------------------------


def _cost(model: str, tokens_in: int, tokens_out: int) -> float:
    return provider_for_model(model).cost(model, tokens_in, tokens_out)


def cost(model: str, tokens_in: int, tokens_out: int) -> float:
    """Public USD cost for an (input, output) token split — used by the estimator."""
    return _cost(model, tokens_in, tokens_out)


# --- token counting ---------------------------------------------------------


def estimate_input_tokens(system: Optional[str], prompt: str) -> int:
    """Offline (~±15-20%) input-token estimate — no key, no network. The shared
    char/token heuristic; NOT a real tokenizer. Use `count_input_tokens()` for
    exact numbers."""
    return heuristic_input_tokens(system, prompt)


def count_input_tokens(
    model: str, system: Optional[str], prompt: str, api_key: Optional[str] = None
) -> int:
    """Exact input-token count for a model, via its provider. May make a (free)
    API call for Anthropic/Gemini, or run locally (tiktoken) for OpenAI. Call only
    when `available(model, api_key)` is True; callers wrap it in try/except."""
    return provider_for_model(model).count_input_tokens(model, system, prompt, api_key)


# --- generation -------------------------------------------------------------


def complete(
    prompt: str,
    model: str = DEFAULT_MODEL,
    system: Optional[str] = None,
    max_tokens: int = 1024,
    api_key: Optional[str] = None,
) -> Completion:
    """One model call (any provider), with latency/token/cost accounting attached."""
    return provider_for_model(model).complete(prompt, model, system, max_tokens, api_key)


# --- judge ------------------------------------------------------------------


@dataclass
class Judgment:
    score: Optional[float]  # normalized to 0..1, or None if unparseable
    rationale: str
    completion: Completion


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_judgment(text: str) -> Tuple[Optional[float], str]:
    """Pull {"score": 1-5, "rationale": "..."} out of the model's reply.

    Defensive on purpose: a judge that occasionally wraps its JSON in prose
    shouldn't crash a whole run. Accepts a 1–5 rating or an already-0–1 score.
    """
    match = _JSON_RE.search(text)
    if match:
        try:
            data = json.loads(match.group(0))
            raw = float(data["score"])
            score = raw / 5.0 if raw > 1.0 else raw
            rationale = str(data.get("rationale", "")).strip()
            return max(0.0, min(1.0, score)), rationale
        except (ValueError, KeyError, TypeError):
            pass
    return None, text.strip()


def judge(
    system: str, prompt: str, model: str = DEFAULT_MODEL, api_key: Optional[str] = None
) -> Judgment:
    completion = complete(
        prompt, model=model, system=system, max_tokens=JUDGE_MAX_TOKENS, api_key=api_key
    )
    score, rationale = _parse_judgment(completion.text)
    return Judgment(score=score, rationale=rationale, completion=completion)
