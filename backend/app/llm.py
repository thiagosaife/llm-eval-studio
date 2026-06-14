"""The one place the backend talks to an LLM provider (doc §5.2, Phase 3).

Defaults to Claude via the official `anthropic` SDK, which reads `ANTHROPIC_API_KEY`
from the environment. Everything is lazy: the client is created on first use, so
the server boots instantly and `GET /api/metrics` stays fast. If the key (or the
SDK) is missing, `available()` is False and the judge/RAG metrics + live
generation are greyed out in the UI rather than failing.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

DEFAULT_MODEL = "claude-opus-4-8"

# Selectable models, newest/strongest first (label shown in the UI).
MODELS = [
    ("claude-opus-4-8", "Claude Opus 4.8"),
    ("claude-sonnet-4-6", "Claude Sonnet 4.6"),
    ("claude-haiku-4-5", "Claude Haiku 4.5"),
]

# USD per 1M tokens: (input, output).
PRICING: Dict[str, Tuple[float, float]] = {
    "claude-opus-4-8": (5.0, 25.0),
    "claude-opus-4-7": (5.0, 25.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-fable-5": (10.0, 50.0),
}

# Output cap per judge call, and the expected output size used for cost estimates.
# A judge reply is a tiny `{"score", "rationale"}` JSON — far below the cap — so
# the estimator reports both an expected cost (~JUDGE_OUTPUT_TOKENS_EST) and a
# guaranteed worst-case ceiling (JUDGE_MAX_TOKENS).
JUDGE_MAX_TOKENS = 1024
JUDGE_OUTPUT_TOKENS_EST = 80

# Offline token heuristic: ~4 chars/token, plus a little per-message overhead.
_CHARS_PER_TOKEN = 4
_MESSAGE_TOKEN_OVERHEAD = 8


def sdk_installed() -> bool:
    """True if the `anthropic` SDK is importable, regardless of credentials.

    Lets the estimator (and the UI) tell "no API key yet" — where a cost
    *estimate* is still possible — apart from "SDK not installed" — where it
    isn't.
    """
    return importlib.util.find_spec("anthropic") is not None


def available() -> bool:
    """True only if the SDK is importable AND a credential is present."""
    if not sdk_installed():
        return False
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))


def unavailable_reason() -> str:
    if importlib.util.find_spec("anthropic") is None:
        return "Run `pip install anthropic` and set ANTHROPIC_API_KEY to enable."
    return "Set ANTHROPIC_API_KEY in the backend environment to enable."


def _cost(model: str, tokens_in: int, tokens_out: int) -> float:
    price_in, price_out = PRICING.get(model, PRICING[DEFAULT_MODEL])
    return round(tokens_in / 1e6 * price_in + tokens_out / 1e6 * price_out, 6)


def cost(model: str, tokens_in: int, tokens_out: int) -> float:
    """Public USD cost for an (input, output) token split — used by the estimator."""
    return _cost(model, tokens_in, tokens_out)


def estimate_input_tokens(system: str, prompt: str) -> int:
    """Offline (~±15-20%) input-token estimate — no key, no network.

    A deliberate char/token heuristic. NOT `tiktoken`, which is OpenAI's
    tokenizer and undercounts Claude; use `count_input_tokens()` when you need
    exact numbers.
    """
    chars = len(system or "") + len(prompt or "")
    return (chars + _CHARS_PER_TOKEN - 1) // _CHARS_PER_TOKEN + _MESSAGE_TOKEN_OVERHEAD


def count_input_tokens(model: str, system: Optional[str], prompt: str) -> int:
    """Exact input-token count via Anthropic's `count_tokens` endpoint.

    This is free — it does not run the model — but it does make an API call, so
    it needs a credential. Call only when `available()` is True.
    """
    client = _get_client()
    kwargs: dict = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    if system:
        kwargs["system"] = system
    return client.messages.count_tokens(**kwargs).input_tokens


@dataclass
class Completion:
    text: str
    model: str
    latency_ms: float
    tokens_in: int
    tokens_out: int
    cost: float


_client = None


def _get_client():
    global _client
    if _client is None:
        import anthropic

        _client = anthropic.Anthropic()
    return _client


def complete(
    prompt: str,
    model: str = DEFAULT_MODEL,
    system: Optional[str] = None,
    max_tokens: int = 1024,
) -> Completion:
    """One Claude call, with latency/token/cost accounting attached."""
    client = _get_client()
    kwargs: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system

    start = time.perf_counter()
    resp = client.messages.create(**kwargs)
    latency_ms = round((time.perf_counter() - start) * 1000, 1)

    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    tokens_in = resp.usage.input_tokens
    tokens_out = resp.usage.output_tokens
    return Completion(
        text=text.strip(),
        model=model,
        latency_ms=latency_ms,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost=_cost(model, tokens_in, tokens_out),
    )


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


def judge(system: str, prompt: str, model: str = DEFAULT_MODEL) -> Judgment:
    completion = complete(prompt, model=model, system=system, max_tokens=JUDGE_MAX_TOKENS)
    score, rationale = _parse_judgment(completion.text)
    return Judgment(score=score, rationale=rationale, completion=completion)
