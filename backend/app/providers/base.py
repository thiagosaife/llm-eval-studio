"""The provider abstraction: one class per LLM vendor (doc §5.2).

Each provider knows how to talk to its SDK, what its models cost, and how to
count tokens. Everything is lazy and import-guarded — a provider whose SDK is
absent (or whose key is missing) simply reports itself unavailable so the UI can
grey it out, exactly as the single-provider build did for Anthropic.

`app/llm.py` is a thin facade over the registry in `__init__.py`; the rest of the
app (api.py, the judge metric, the estimator) routes by *model id* and never
imports a concrete provider.
"""
from __future__ import annotations

import importlib.util
import os
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# Offline token heuristic, shared by every provider: ~4 chars/token plus a little
# per-message overhead. Deliberately NOT a real tokenizer — used when no exact
# count is available (no key, or the provider can't count offline). Providers that
# *can* count exactly (OpenAI via tiktoken, Anthropic/Gemini via their APIs)
# override count_input_tokens().
_CHARS_PER_TOKEN = 4
_MESSAGE_TOKEN_OVERHEAD = 8


def heuristic_input_tokens(system: Optional[str], prompt: str) -> int:
    chars = len(system or "") + len(prompt or "")
    return (chars + _CHARS_PER_TOKEN - 1) // _CHARS_PER_TOKEN + _MESSAGE_TOKEN_OVERHEAD


@dataclass
class Completion:
    """One model call, with latency/token/cost accounting attached."""

    text: str
    model: str
    latency_ms: float
    tokens_in: int
    tokens_out: int
    cost: float


class Provider:
    """Base class for an LLM vendor. Subclasses set the class attributes and
    implement `_create()` (the raw SDK call) — everything else is shared.

    To add a provider: write one subclass, register it in `providers/__init__.py`.
    """

    id: str = ""
    name: str = ""
    sdk_module: str = ""  # import name probed without importing the heavy lib
    env_vars: Tuple[str, ...] = ()  # first one present wins; first listed is canonical
    install_pip: str = ""  # `pip install <x>` hint
    # Selectable models, strongest/newest first: (model_id, UI label).
    models: List[Tuple[str, str]] = []
    # USD per 1M tokens: {model_id: (input, output)}.
    pricing: Dict[str, Tuple[float, float]] = {}

    # --- availability -------------------------------------------------------

    def sdk_installed(self) -> bool:
        """True if the SDK is importable, regardless of credentials. Tolerates a
        dotted module whose parent package is absent (find_spec would raise)."""
        try:
            return importlib.util.find_spec(self.sdk_module) is not None
        except ModuleNotFoundError:
            return False

    def env_key(self) -> Optional[str]:
        for var in self.env_vars:
            value = os.getenv(var)
            if value:
                return value
        return None

    def resolve_key(self, api_key: Optional[str] = None) -> Optional[str]:
        """A request-supplied key wins; otherwise fall back to the environment."""
        return (api_key or "").strip() or self.env_key()

    def available(self, api_key: Optional[str] = None) -> bool:
        """True only if the SDK is importable AND a credential is present."""
        return self.sdk_installed() and bool(self.resolve_key(api_key))

    def unavailable_reason(self, api_key: Optional[str] = None) -> str:
        if not self.sdk_installed():
            return f"Run `pip install {self.install_pip}` to enable {self.name}."
        return f"Add a {self.name} API key ({self.env_vars[0]}) to enable it."

    # --- pricing ------------------------------------------------------------

    def cost(self, model: str, tokens_in: int, tokens_out: int) -> float:
        price_in, price_out = self.pricing.get(model, next(iter(self.pricing.values())))
        return round(tokens_in / 1e6 * price_in + tokens_out / 1e6 * price_out, 6)

    # --- token counting -----------------------------------------------------

    def count_input_tokens(
        self, model: str, system: Optional[str], prompt: str, api_key: Optional[str] = None
    ) -> int:
        """Exact input-token count. Default: the offline heuristic. Subclasses
        override when they have a real tokenizer (tiktoken) or a count endpoint."""
        return heuristic_input_tokens(system, prompt)

    # --- generation ---------------------------------------------------------

    def _create(
        self, prompt: str, model: str, system: Optional[str], max_tokens: int, api_key: Optional[str]
    ) -> Tuple[str, int, int]:
        """Make the raw SDK call. Returns (text, tokens_in, tokens_out)."""
        raise NotImplementedError

    def complete(
        self,
        prompt: str,
        model: str,
        system: Optional[str] = None,
        max_tokens: int = 1024,
        api_key: Optional[str] = None,
    ) -> Completion:
        start = time.perf_counter()
        text, tokens_in, tokens_out = self._create(prompt, model, system, max_tokens, api_key)
        latency_ms = round((time.perf_counter() - start) * 1000, 1)
        return Completion(
            text=text.strip(),
            model=model,
            latency_ms=latency_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost=self.cost(model, tokens_in, tokens_out),
        )
