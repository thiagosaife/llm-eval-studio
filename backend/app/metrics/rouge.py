"""ROUGE-1 / ROUGE-2 / ROUGE-L, implemented in pure Python (doc §3.1).

ROUGE is recall-oriented n-gram overlap — "how much of the reference did the
output capture?" We report the F-measure (the harmonic mean of precision and
recall) for each variant, which is what most tooling shows.

Implemented from scratch rather than pulling in `rouge-score` so Phase 1 stays
dependency-light and instant. The logic is small and standard; the test suite
pins it against hand-computed values so it can't drift (an eval tool getting
its own metric subtly wrong would be the worst kind of bug).
"""
from __future__ import annotations

import re
from collections import Counter
from typing import List, Optional, Tuple

from .base import BaseMetric

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> List[str]:
    return _TOKEN.findall(text.lower())


def _f1(precision: float, recall: float) -> float:
    if precision + recall == 0.0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _ngrams(tokens: List[str], n: int) -> List[Tuple[str, ...]]:
    return [tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def ngram_f1(prediction: str, reference: str, n: int) -> float:
    pred = _ngrams(tokenize(prediction), n)
    ref = _ngrams(tokenize(reference), n)
    if not pred or not ref:
        return 0.0
    # Clipped overlap: a prediction n-gram only counts up to how often it
    # actually appears in the reference (Counter intersection does this).
    overlap = sum((Counter(pred) & Counter(ref)).values())
    if overlap == 0:
        return 0.0
    return _f1(overlap / len(pred), overlap / len(ref))


def _lcs_length(a: List[str], b: List[str]) -> int:
    """Length of the longest common subsequence (classic DP, O(m*n))."""
    m, n = len(a), len(b)
    prev = [0] * (n + 1)
    for i in range(1, m + 1):
        curr = [0] * (n + 1)
        ai = a[i - 1]
        for j in range(1, n + 1):
            if ai == b[j - 1]:
                curr[j] = prev[j - 1] + 1
            else:
                curr[j] = prev[j] if prev[j] >= curr[j - 1] else curr[j - 1]
        prev = curr
    return prev[n]


def rouge_l_f1(prediction: str, reference: str) -> float:
    pred = tokenize(prediction)
    ref = tokenize(reference)
    if not pred or not ref:
        return 0.0
    lcs = _lcs_length(pred, ref)
    if lcs == 0:
        return 0.0
    return _f1(lcs / len(pred), lcs / len(ref))


class _RougeN(BaseMetric):
    """Shared body for the ROUGE-1 and ROUGE-2 metrics."""

    n: int

    def score(
        self,
        prediction: str,
        reference: Optional[str],
        context: Optional[str] = None,
    ) -> float:
        if reference is None:
            return 0.0
        return ngram_f1(prediction, reference, self.n)


class Rouge1(_RougeN):
    n = 1
    info = None  # populated below, once MetricInfo is imported


class Rouge2(_RougeN):
    n = 2
    info = None


class RougeL(BaseMetric):
    info = None  # populated below

    def score(
        self,
        prediction: str,
        reference: Optional[str],
        context: Optional[str] = None,
    ) -> float:
        if reference is None:
            return 0.0
        return rouge_l_f1(prediction, reference)


# --- metric metadata --------------------------------------------------------
# Imported here (not at top) to keep the math above import-light and testable.
from ..models import MetricInfo  # noqa: E402

Rouge1.info = MetricInfo(
    id="rouge1",
    name="ROUGE-1",
    family="lexical",
    description="F1 of single-word (unigram) overlap with the reference.",
    requires_reference=True,
    range=[0.0, 1.0],
    how_to_read="Higher = the output reuses more of the reference's words. Recall-leaning.",
    caveat="Blind to meaning — a correct paraphrase using synonyms scores low.",
)
Rouge2.info = MetricInfo(
    id="rouge2",
    name="ROUGE-2",
    family="lexical",
    description="F1 of word-pair (bigram) overlap — rewards matching word order.",
    requires_reference=True,
    range=[0.0, 1.0],
    how_to_read="Stricter than ROUGE-1; sensitive to phrasing, not just vocabulary.",
    caveat="Drops fast on valid rewordings; near zero for short or reordered text.",
)
RougeL.info = MetricInfo(
    id="rougeL",
    name="ROUGE-L",
    family="lexical",
    description="F1 based on the longest common subsequence with the reference.",
    requires_reference=True,
    range=[0.0, 1.0],
    how_to_read="Captures in-order overlap without needing contiguous matches.",
    caveat="Still lexical — synonyms hurt it, and high recall isn't conciseness.",
)
