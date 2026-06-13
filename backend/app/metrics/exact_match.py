"""Exact Match — the simplest reference-based metric (doc §3.1)."""
from __future__ import annotations

import re
from typing import Optional

from ..models import MetricInfo
from .base import BaseMetric

_WS = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Light normalization: lowercase, collapse whitespace, strip ends.

    Deliberately conservative — EM is meant to be strict. We don't strip
    punctuation, because for the closed questions EM is good at ("What's the
    capital of France?") punctuation rarely differs and over-normalizing
    would hide real mismatches.
    """
    return _WS.sub(" ", text.strip().lower())


class ExactMatch(BaseMetric):
    info = MetricInfo(
        id="exact_match",
        name="Exact Match",
        family="lexical",
        description=(
            "1.0 if the output equals the reference after light normalization "
            "(lowercasing, whitespace), else 0.0."
        ),
        requires_reference=True,
        range=[0.0, 1.0],
        how_to_read="Binary. Use it for closed questions with a single right answer.",
        caveat="Useless for free-form text — one extra word makes a correct answer fail.",
    )

    def score(
        self,
        prediction: str,
        reference: Optional[str],
        context: Optional[str] = None,
    ) -> float:
        if reference is None:
            return 0.0
        return 1.0 if normalize(prediction) == normalize(reference) else 0.0
