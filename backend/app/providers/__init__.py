"""Provider registry: id -> Provider, and model id -> Provider.

This is the multi-provider extension seam. To add a vendor, implement `Provider`
(see base.py) and append an instance to `_PROVIDERS`; it then appears in
`GET /api/providers`, the model pickers, and the cost estimator automatically.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .anthropic_provider import AnthropicProvider
from .base import Completion, Provider
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider

# Display order across the app: Anthropic (the default), then OpenAI, then Gemini.
_PROVIDERS: List[Provider] = [
    AnthropicProvider(),
    OpenAIProvider(),
    GeminiProvider(),
]

PROVIDERS: Dict[str, Provider] = {p.id: p for p in _PROVIDERS}

# model id -> provider, built once from each provider's declared model list.
_MODEL_INDEX: Dict[str, Provider] = {
    model_id: provider for provider in _PROVIDERS for model_id, _ in provider.models
}

DEFAULT_MODEL = "claude-opus-4-8"


def all_providers() -> List[Provider]:
    return list(_PROVIDERS)


def get_provider(provider_id: str) -> Optional[Provider]:
    return PROVIDERS.get(provider_id)


def provider_for_model(model: str) -> Provider:
    """Resolve the provider that owns a model id, defaulting to the model's
    declared owner, then to the default model's provider for unknown ids (so a
    stray/legacy id still costs/runs as Claude rather than crashing)."""
    provider = _MODEL_INDEX.get(model)
    if provider is not None:
        return provider
    # Unknown id: prefix-match a known provider's family, else fall back to default.
    for prov in _PROVIDERS:
        if any(model.startswith(mid.split("-")[0]) for mid, _ in prov.models):
            return prov
    return _MODEL_INDEX[DEFAULT_MODEL]


def all_models() -> List[Tuple[str, str, str]]:
    """Every selectable model across providers: (model_id, label, provider_id)."""
    return [(mid, label, prov.id) for prov in _PROVIDERS for mid, label in prov.models]


def any_sdk() -> bool:
    """True if at least one provider's SDK is importable (drives estimable)."""
    return any(p.sdk_installed() for p in _PROVIDERS)


def any_available() -> bool:
    """True if at least one provider has both its SDK and a credential."""
    return any(p.available() for p in _PROVIDERS)


__all__ = [
    "Completion",
    "Provider",
    "PROVIDERS",
    "DEFAULT_MODEL",
    "all_providers",
    "get_provider",
    "provider_for_model",
    "all_models",
    "any_sdk",
    "any_available",
]
