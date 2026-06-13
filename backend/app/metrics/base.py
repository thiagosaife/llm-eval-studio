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
from typing import List, Optional

from ..models import MetricInfo


@dataclass
class Scored:
    """One case as seen by `aggregate()`: its text plus its per-case score."""

    prediction: Optional[str]
    reference: Optional[str]
    context: Optional[str]
    value: Optional[float]


class BaseMetric(ABC):
    info: MetricInfo
    # Import names this metric needs to run. The registry checks them (without
    # importing the heavy library) to set `info.available`. Empty = always on.
    requires_modules: tuple = ()
    install_hint: Optional[str] = None

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

    def aggregate(self, scored: List[Scored]) -> Optional[float]:
        """Summarise a run. Default: mean of the applicable per-case scores."""
        values = [s.value for s in scored if s.value is not None]
        if not values:
            return None
        return round(sum(values) / len(values), 4)
