"""Google Gemini provider — the current `google-genai` SDK (doc §5.2).

Uses `from google import genai` (the unified SDK that replaced
`google-generativeai`). The system prompt goes in `GenerateContentConfig.
system_instruction`; usage comes back on `usage_metadata`. Exact token counting
uses `client.models.count_tokens`, which needs a key — the caller wraps it in
try/except and falls back to the heuristic (mirroring Anthropic's path).
"""
from __future__ import annotations

from typing import Optional, Tuple

from .base import Provider


class GeminiProvider(Provider):
    id = "gemini"
    name = "Google (Gemini)"
    sdk_module = "google.genai"
    env_vars = ("GEMINI_API_KEY", "GOOGLE_API_KEY")
    install_pip = "google-genai"

    models = [
        ("gemini-2.5-pro", "Gemini 2.5 Pro"),
        ("gemini-2.5-flash", "Gemini 2.5 Flash"),
        ("gemini-2.0-flash", "Gemini 2.0 Flash"),
    ]
    # USD per 1M tokens (input, output) — base tier; large-context tiers cost more.
    pricing = {
        "gemini-2.5-pro": (1.25, 10.0),
        "gemini-2.5-flash": (0.3, 2.5),
        "gemini-2.0-flash": (0.1, 0.4),
    }

    def _client(self, api_key: Optional[str]):
        from google import genai

        key = self.resolve_key(api_key)
        return genai.Client(api_key=key)

    def _config(self, system: Optional[str], max_tokens: Optional[int]):
        from google.genai import types

        kwargs: dict = {}
        if system:
            kwargs["system_instruction"] = system
        if max_tokens is not None:
            kwargs["max_output_tokens"] = max_tokens
        return types.GenerateContentConfig(**kwargs) if kwargs else None

    def count_input_tokens(
        self, model: str, system: Optional[str], prompt: str, api_key: Optional[str] = None
    ) -> int:
        client = self._client(api_key)
        # count_tokens has no system_instruction slot, so fold it into the text —
        # close enough for an estimate.
        contents = (system + "\n\n" if system else "") + prompt
        return client.models.count_tokens(model=model, contents=contents).total_tokens

    def _create(
        self, prompt: str, model: str, system: Optional[str], max_tokens: int, api_key: Optional[str]
    ) -> Tuple[str, int, int]:
        client = self._client(api_key)
        resp = client.models.generate_content(
            model=model, contents=prompt, config=self._config(system, max_tokens)
        )
        text = resp.text or ""
        usage = resp.usage_metadata
        tokens_in = getattr(usage, "prompt_token_count", 0) or 0
        tokens_out = getattr(usage, "candidates_token_count", 0) or 0
        return text, tokens_in, tokens_out
