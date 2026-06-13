"""Pydantic schemas — the contract the Vue typed client mirrors.

Keep these in sync with `frontend/src/api/types.ts`; that one-to-one
correspondence is what keeps the app type-safe end to end (doc §6).
"""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class MetricInfo(BaseModel):
    """Self-describing metadata for one metric.

    Returned by `GET /api/metrics` and used by the frontend to drive the
    metric picker AND the inline "what this tells you / when it lies"
    teaching notes (doc §3, §6.2).
    """

    id: str
    name: str
    family: str  # lexical | semantic | classification | model_judge | rag | operational
    description: str
    requires_reference: bool
    range: List[float] = Field(default_factory=lambda: [0.0, 1.0])
    how_to_read: str
    caveat: str
    # Whether the metric can run right now. Embedding metrics flip this to False
    # until their (heavy) ML libraries are installed, so the picker can grey
    # them out instead of letting a run fail.
    available: bool = True
    unavailable_reason: Optional[str] = None
    # Precision/Recall/F1 are *set-level* — they have no meaningful per-case
    # value, only an aggregate. Such metrics are shown as summary cards but
    # omitted from the per-case table.
    aggregate_only: bool = False


class TestCase(BaseModel):
    """One row of a dataset (doc §7)."""

    id: str
    input: Optional[str] = None  # the prompt / question
    prediction: Optional[str] = None  # the LLM output (pasted, imported, or generated)
    reference: Optional[str] = None  # gold answer — enables reference-based metrics
    context: Optional[str] = None  # retrieved docs — enables RAG metrics


class DatasetCreate(BaseModel):
    name: str
    cases: List[TestCase] = Field(default_factory=list)


class Dataset(BaseModel):
    id: str
    name: str
    cases: List[TestCase] = Field(default_factory=list)


class EvaluateRequest(BaseModel):
    """The main call (doc §5.5)."""

    metrics: List[str]
    cases: List[TestCase]
    dataset_id: Optional[str] = None
    dataset_name: Optional[str] = None


class CaseResult(BaseModel):
    """Per-case scores, plus the text needed for the inspector view."""

    id: str
    input: Optional[str] = None
    prediction: Optional[str] = None
    reference: Optional[str] = None
    context: Optional[str] = None
    # `None` means "not applicable" (e.g. a reference-based metric with no
    # reference). The frontend renders that as a dash, not a zero.
    scores: Dict[str, Optional[float]]


class ConfusionMatrix(BaseModel):
    """Full right/wrong breakdown per class — what you actually look at to debug
    a classification task (doc §3.3). `matrix[i][j]` = cases whose true label is
    `labels[i]` and predicted label is `labels[j]`; the diagonal is correct."""

    labels: List[str]
    matrix: List[List[int]]


class RunResponse(BaseModel):
    run_id: str
    created_at: str
    dataset_name: Optional[str] = None
    metrics: List[str]
    per_case: List[CaseResult]
    aggregate: Dict[str, Optional[float]]
    # Present only when a classification metric was run.
    confusion_matrix: Optional[ConfusionMatrix] = None
