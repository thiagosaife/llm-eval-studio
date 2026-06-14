"""Shared sentence-embedding helper.

One place loads the `all-MiniLM-L6-v2` model and turns text into vectors, used by
both the Cosine-similarity metric (`metrics/embeddings.py`) and the
dimensionality-reduction explorer (`projection.py`). Keeping it here means the
(heavy) model is loaded once and cached, and both callers stay in lockstep.

Everything is lazy: nothing imports `sentence_transformers` until `embed_texts`
is actually called, so the server still boots instantly and `GET /api/metrics`
stays fast. `available()` lets the API grey the feature out when the library
isn't installed, exactly like the metric registry does.
"""
from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:  # numpy is only needed at call time, alongside the model
    import numpy as np

MODEL_NAME = "all-MiniLM-L6-v2"

# Cached SentenceTransformer, loaded on first use.
_model = None


def available() -> bool:
    """True iff the embedding stack is importable."""
    return importlib.util.find_spec("sentence_transformers") is not None


def unavailable_reason() -> str:
    return "Embeddings need sentence-transformers — `pip install sentence-transformers`."


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed_texts(texts: List[str]) -> "np.ndarray":
    """Embed a list of texts into an (n, dim) float array of L2-normalized vectors.

    Normalized so that cosine similarity is a plain dot product and so the
    projection algorithms see comparable scales.
    """
    model = _get_model()
    return model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
