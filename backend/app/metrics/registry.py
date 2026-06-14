"""The metric registry: id -> metric instance (doc §5.4).

`GET /api/metrics` reads `all_infos()`, and `POST /api/evaluate` resolves
selected ids through `get()`. To add a metric, implement `BaseMetric` and append
an instance to `_DEFAULTS` — nothing else changes.

At registration we probe each metric's `requires_modules` (without importing the
heavy library) and flip `info.available` off if anything is missing, so the UI
can grey the metric out instead of letting a run fail.
"""
from __future__ import annotations

import importlib.util
from typing import Dict, List

from .. import llm
from ..models import MetricInfo
from .base import BaseMetric
from .classification import Accuracy, F1Macro, PrecisionMacro, RecallMacro
from .embeddings import BERTScore, CosineSimilarity
from .exact_match import ExactMatch
from .judge import AnswerRelevancy, ContextRelevancy, Faithfulness, LLMJudge
from .rouge import Rouge1, Rouge2, RougeL

_REGISTRY: Dict[str, BaseMetric] = {}


def _missing_modules(metric: BaseMetric) -> List[str]:
    return [m for m in metric.requires_modules if importlib.util.find_spec(m) is None]


def register(metric: BaseMetric) -> None:
    if metric.requires_llm:
        # Needs both the SDK and a credential — reflect whichever is missing.
        metric.info.available = llm.available()
        if not metric.info.available:
            metric.info.unavailable_reason = llm.unavailable_reason()
        # A cost *estimate* only needs the SDK (it's free / can run offline), so a
        # missing key leaves the metric estimable even though it isn't runnable.
        metric.info.estimable = llm.sdk_installed()
    else:
        missing = _missing_modules(metric)
        if missing:
            metric.info.available = False
            hint = metric.install_hint or f"install: {', '.join(missing)}"
            metric.info.unavailable_reason = f"Needs {', '.join(missing)} — {hint}"
        metric.info.estimable = metric.info.available
    _REGISTRY[metric.info.id] = metric


def get(metric_id: str) -> BaseMetric | None:
    return _REGISTRY.get(metric_id)


def all_infos() -> List[MetricInfo]:
    return [m.info for m in _REGISTRY.values()]


# Registration order is the display order in the picker: cheap/instant first,
# then classification, the heavier semantic metrics, then the LLM-judged ones.
_DEFAULTS: List[BaseMetric] = [
    ExactMatch(),
    Rouge1(),
    Rouge2(),
    RougeL(),
    Accuracy(),
    PrecisionMacro(),
    RecallMacro(),
    F1Macro(),
    CosineSimilarity(),
    BERTScore(),
    LLMJudge(),
    Faithfulness(),
    AnswerRelevancy(),
    ContextRelevancy(),
]
for _m in _DEFAULTS:
    register(_m)
