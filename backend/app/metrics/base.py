"""The common interface every metric implements (doc §5.4).

The point of this shape: the API layer never needs to know which *family* a
metric belongs to. A lexical scorer, an embedding scorer, and a classification
scorer all look identical from the outside. Adding a metric is "write one class,
register it," and it shows up in the UI automatically because `GET /api/metrics`
reads the registry.

Two hooks:
- `score()` — the per-case value shown in the results table.
- `aggregate()` — the single summary number. The default is the mean of the
  per-case scores, which is right for overlap/similarity metrics. Set-level
  metrics (precision, recall, F1) override it to compute over all labels at
  once, because those quantities are *not* a mean of per-case values.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional

from ..models import MetricInfo

if TYPE_CHECKING:
    from ..llm import Completion
    from ..models import JudgeConfig, TestCase


@dataclass
class Scored:
    """One case as seen by `aggregate()`: its text plus its per-case score."""

    prediction: Optional[str]
    reference: Optional[str]
    context: Optional[str]
    value: Optional[float]


@dataclass
class MetricOutput:
    """What an LLM/judge metric returns per case: a score, plus the judge's
    written rationale and the cost of producing it (doc §7)."""

    value: Optional[float]
    rationale: Optional[str] = None
    completion: Optional["Completion"] = None


class BaseMetric(ABC):
    info: MetricInfo
    # Import names this metric needs to run. The registry checks them (without
    # importing the heavy library) to set `info.available`. Empty = always on.
    requires_modules: tuple = ()
    install_hint: Optional[str] = None
    # LLM/judge metrics set this True: the engine routes them through
    # `judge()` (which returns a rationale) instead of `score()`.
    requires_llm: bool = False

    @abstractmethod
    def score(
        self,
        prediction: str,
        reference: Optional[str],
        context: Optional[str] = None,
    ) -> float:
        """Score one case in `info.range` (almost always [0, 1]).

        The engine guarantees the inputs a metric requires are non-empty before
        calling (see app/api.py), so implementations can assume what they need.
        """
        ...

    def judge(self, case: "TestCase", config: Optional["JudgeConfig"]) -> "MetricOutput":
        """LLM-judged metrics override this to call the model and return a
        score + rationale. Non-LLM metrics never reach it."""
        raise NotImplementedError

    def aggregate(self, scored: List[Scored]) -> Optional[float]:
        """Summarise a run. Default: mean of the applicable per-case scores."""
        values = [s.value for s in scored if s.value is not None]
        if not values:
            return None
        return round(sum(values) / len(values), 4)
