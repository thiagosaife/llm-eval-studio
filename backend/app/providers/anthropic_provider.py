"""Anthropic / Claude provider — the original single-provider path (doc §5.2).

Uses the official `anthropic` SDK. `messages.count_tokens` is free (it doesn't run
the model) but still needs a credential AND a funded balance — the caller wraps it
in try/except and falls back to the heuristic, so an unfunded key degrades cleanly.
"""
from __future__ import annotations

from typing import Optional, Tuple

from .base import Provider


class AnthropicProvider(Provider):
    id = "anthropic"
    name = "Anthropic (Claude)"
    sdk_module = "anthropic"
    env_vars = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")
    install_pip = "anthropic"

    # Newest/strongest first. IDs and pricing verified against the claude-api skill.
    models = [
        ("claude-opus-4-8", "Claude Opus 4.8"),
        ("claude-sonnet-4-6", "Claude Sonnet 4.6"),
        ("claude-haiku-4-5", "Claude Haiku 4.5"),
        ("claude-fable-5", "Claude Fable 5"),
    ]
    pricing = {
        "claude-opus-4-8": (5.0, 25.0),
        "claude-opus-4-7": (5.0, 25.0),
        "claude-sonnet-4-6": (3.0, 15.0),
        "claude-haiku-4-5": (1.0, 5.0),
        "claude-fable-5": (10.0, 50.0),
    }

    def _client(self, api_key: Optional[str]):
        import anthropic

        # Pass the key explicitly when supplied; otherwise let the SDK read the env.
        return anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    def count_input_tokens(
        self, model: str, system: Optional[str], prompt: str, api_key: Optional[str] = None
    ) -> int:
        client = self._client(self.resolve_key(api_key))
        kwargs: dict = {"model": model, "messages": [{"role": "user", "content": prompt}]}
        if system:
            kwargs["system"] = system
        return client.messages.count_tokens(**kwargs).input_tokens

    def _create(
        self, prompt: str, model: str, system: Optional[str], max_tokens: int, api_key: Optional[str]
    ) -> Tuple[str, int, int]:
        client = self._client(self.resolve_key(api_key))
        kwargs: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        resp = client.messages.create(**kwargs)
        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        return text, resp.usage.input_tokens, resp.usage.output_tokens
