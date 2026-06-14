"""Semantic / embedding metrics (doc §3.2).

Unlike the lexical metrics, these reward correct paraphrases — they compare
*meaning* by turning text into vectors. They need heavy ML libraries (PyTorch +
models), so:

- The libraries are imported lazily, inside `score()`, and the model is loaded
  once and cached on the class. Nothing heavy happens at import time, so the
  server boots instantly and `GET /api/metrics` stays fast.
- `requires_modules` lets the registry mark them unavailable (greyed out in the
  picker) until the libraries are installed.
"""
from __future__ import annotations

from typing import Optional

from ..models import MetricInfo
from .base import BaseMetric


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


class CosineSimilarity(BaseMetric):
    requires_modules = ("sentence_transformers",)
    install_hint = "pip install sentence-transformers"

    info = MetricInfo(
        id="cosine",
        name="Cosine similarity",
        family="semantic",
        description="Cosine of sentence-embedding vectors for the output and the reference.",
        requires_reference=True,
        range=[0.0, 1.0],
        how_to_read="Quick 'are these two answers about the same thing?' signal.",
        caveat="Coarser than BERTScore; fluent but wrong text can still sit close.",
    )

    def score(
        self,
        prediction: str,
        reference: Optional[str],
        context: Optional[str] = None,
    ) -> float:
        if not reference:
            return 0.0
        # Shared model + lazy load with the projection explorer (embeddings_util).
        from .. import embeddings_util

        emb = embeddings_util.embed_texts([prediction, reference])
        return _clamp01(float(emb[0] @ emb[1]))


class BERTScore(BaseMetric):
    requires_modules = ("bert_score", "torch")
    install_hint = "pip install bert-score"
    _scorer = None  # cached BERTScorer

    info = MetricInfo(
        id="bertscore",
        name="BERTScore",
        family="semantic",
        description="Token-level contextual-embedding match (F1), rescaled with a baseline.",
        requires_reference=True,
        range=[0.0, 1.0],
        how_to_read="A correct paraphrase scores high even with zero word overlap.",
        caveat="Semantic closeness ≠ correctness — fluent, on-topic, factually wrong still scores high.",
    )

    @classmethod
    def _get_scorer(cls):
        if cls._scorer is None:
            from bert_score import BERTScorer

            # bert-base-uncased keeps the download modest (~0.4 GB) and has a
            # rescaling baseline, which spreads scores into a readable range.
            cls._scorer = BERTScorer(
                model_type="bert-base-uncased", lang="en", rescale_with_baseline=True
            )
        return cls._scorer

    def score(
        self,
        prediction: str,
        reference: Optional[str],
        context: Optional[str] = None,
    ) -> float:
        if not reference:
            return 0.0
        scorer = self._get_scorer()
        _, _, f1 = scorer.score([prediction], [reference])
        return _clamp01(float(f1[0]))
