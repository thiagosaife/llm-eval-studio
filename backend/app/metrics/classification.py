"""Classification metrics (doc §3.3).

When the LLM task is really classification (sentiment, intent, yes/no,
category), treat it like one. Two wrinkles distinguish these from the
overlap metrics:

1. The per-case signal is just "did the model get this label right?" (1/0).
2. Precision / Recall / F1 are *set-level* — they're computed from the whole
   confusion of labels, not as a mean of per-case values. Those three set
   `aggregate_only=True`, so they appear as summary cards but not as per-case
   table columns (a per-case "precision" would be meaningless).

scikit-learn is imported lazily inside `aggregate()` so the server still boots
if it isn't installed yet; the registry marks these metrics unavailable until
it is.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from ..models import MetricInfo
from .base import BaseMetric, Scored
from .exact_match import normalize


def _labels(scored: List[Scored]) -> Tuple[List[str], List[str]]:
    """Normalized (true, predicted) label lists over the applicable cases."""
    y_true: List[str] = []
    y_pred: List[str] = []
    for s in scored:
        if s.prediction and s.reference:
            y_true.append(normalize(s.reference))
            y_pred.append(normalize(s.prediction))
    return y_true, y_pred


class _ClassificationMetric(BaseMetric):
    requires_modules = ("sklearn",)
    install_hint = "pip install scikit-learn"

    def score(
        self,
        prediction: str,
        reference: Optional[str],
        context: Optional[str] = None,
    ) -> float:
        # Per-case = was this case classified correctly? (Used by Accuracy; the
        # set-level metrics set aggregate_only and never call this.)
        if reference is None:
            return 0.0
        return 1.0 if normalize(prediction) == normalize(reference) else 0.0


class Accuracy(_ClassificationMetric):
    info = MetricInfo(
        id="accuracy",
        name="Accuracy",
        family="classification",
        description="Fraction of cases whose predicted label matches the reference label.",
        requires_reference=True,
        range=[0.0, 1.0],
        how_to_read="The headline 'how often is it right' number.",
        caveat="Misleading on imbalanced data — 95% is bad if 95% of cases are one class.",
    )

    def aggregate(self, scored: List[Scored]) -> Optional[float]:
        from sklearn.metrics import accuracy_score

        y_true, y_pred = _labels(scored)
        if not y_true:
            return None
        return round(float(accuracy_score(y_true, y_pred)), 4)


class PrecisionMacro(_ClassificationMetric):
    info = MetricInfo(
        id="precision",
        name="Precision (macro)",
        family="classification",
        description="Of the cases predicted as a class, how many were right — averaged over classes.",
        requires_reference=True,
        range=[0.0, 1.0],
        how_to_read="Penalizes false alarms. Watch it when wrong positives are costly.",
        caveat="Set-level only (no per-case value). Macro-averaged, so rare classes count equally.",
        aggregate_only=True,
    )

    def aggregate(self, scored: List[Scored]) -> Optional[float]:
        from sklearn.metrics import precision_score

        y_true, y_pred = _labels(scored)
        if not y_true:
            return None
        return round(float(precision_score(y_true, y_pred, average="macro", zero_division=0)), 4)


class RecallMacro(_ClassificationMetric):
    info = MetricInfo(
        id="recall",
        name="Recall (macro)",
        family="classification",
        description="Of the cases truly in a class, how many were caught — averaged over classes.",
        requires_reference=True,
        range=[0.0, 1.0],
        how_to_read="Penalizes misses. Watch it when missing a positive is costly.",
        caveat="Set-level only (no per-case value). Macro-averaged across classes.",
        aggregate_only=True,
    )

    def aggregate(self, scored: List[Scored]) -> Optional[float]:
        from sklearn.metrics import recall_score

        y_true, y_pred = _labels(scored)
        if not y_true:
            return None
        return round(float(recall_score(y_true, y_pred, average="macro", zero_division=0)), 4)


class F1Macro(_ClassificationMetric):
    info = MetricInfo(
        id="f1",
        name="F1 (macro)",
        family="classification",
        description="Harmonic mean of precision and recall, averaged over classes.",
        requires_reference=True,
        range=[0.0, 1.0],
        how_to_read="The single number to watch when you care about both precision and recall.",
        caveat="Set-level only (no per-case value). Macro-averaged across classes.",
        aggregate_only=True,
    )

    def aggregate(self, scored: List[Scored]) -> Optional[float]:
        from sklearn.metrics import f1_score

        y_true, y_pred = _labels(scored)
        if not y_true:
            return None
        return round(float(f1_score(y_true, y_pred, average="macro", zero_division=0)), 4)
