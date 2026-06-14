"""OpenAI provider — the `openai` SDK Chat Completions API (doc §5.2).

Uses `chat.completions.create` with `max_completion_tokens` (the field the GPT-5 /
o-series models require; older models accept it too). Token counts come back on
`usage`. For *offline* exact counts (the estimator's "get exact count" button),
OpenAI's tokenizer `tiktoken` runs locally with no key — `o200k_base` covers the
GPT-4o / GPT-5 families; we fall back to the char heuristic if tiktoken is absent
or doesn't recognize a model.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from .base import Provider, heuristic_input_tokens


class OpenAIProvider(Provider):
    id = "openai"
    name = "OpenAI (GPT)"
    sdk_module = "openai"
    env_vars = ("OPENAI_API_KEY",)
    install_pip = "openai"

    models = [
        ("gpt-5.1", "GPT-5.1"),
        ("gpt-5", "GPT-5"),
        ("gpt-5-mini", "GPT-5 mini"),
        ("gpt-4.1", "GPT-4.1"),
        ("gpt-4o", "GPT-4o"),
        ("gpt-4o-mini", "GPT-4o mini"),
    ]
    # USD per 1M tokens (input, output) — approximate published rates.
    pricing = {
        "gpt-5.1": (1.25, 10.0),
        "gpt-5": (1.25, 10.0),
        "gpt-5-mini": (0.25, 2.0),
        "gpt-4.1": (2.0, 8.0),
        "gpt-4o": (2.5, 10.0),
        "gpt-4o-mini": (0.15, 0.6),
    }

    def _client(self, api_key: Optional[str]):
        from openai import OpenAI

        return OpenAI(api_key=api_key) if api_key else OpenAI()

    def _messages(self, system: Optional[str], prompt: str) -> List[dict]:
        messages: List[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return messages

    def count_input_tokens(
        self, model: str, system: Optional[str], prompt: str, api_key: Optional[str] = None
    ) -> int:
        try:
            import tiktoken

            try:
                enc = tiktoken.encoding_for_model(model)
            except KeyError:
                enc = tiktoken.get_encoding("o200k_base")
            # ~3 tokens of per-message framing each for system + user.
            text = (system or "") + "\n" + prompt
            return len(enc.encode(text)) + (6 if system else 3)
        except Exception:
            return heuristic_input_tokens(system, prompt)

    def _create(
        self, prompt: str, model: str, system: Optional[str], max_tokens: int, api_key: Optional[str]
    ) -> Tuple[str, int, int]:
        client = self._client(self.resolve_key(api_key))
        resp = client.chat.completions.create(
            model=model,
            messages=self._messages(system, prompt),
            max_completion_tokens=max_tokens,
        )
        text = resp.choices[0].message.content or ""
        usage = resp.usage
        return text, usage.prompt_tokens, usage.completion_tokens
