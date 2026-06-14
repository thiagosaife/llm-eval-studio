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
    # RAG metrics need retrieved context; LLM-judge produces a written rationale.
    requires_context: bool = False
    produces_rationale: bool = False


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


class JudgeConfig(BaseModel):
    """Model + rubric for LLM-as-a-judge metrics (doc §3.4)."""

    model: Optional[str] = None
    rubric: Optional[str] = None


class EvaluateRequest(BaseModel):
    """The main call (doc §5.5)."""

    metrics: List[str]
    cases: List[TestCase]
    dataset_id: Optional[str] = None
    dataset_name: Optional[str] = None
    judge: Optional[JudgeConfig] = None


class Operational(BaseModel):
    """Operational metrics for one LLM call (doc §3.6)."""

    latency_ms: float
    tokens_in: int
    tokens_out: int
    cost: float


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
    # metricId -> the judge's written explanation (LLM-judge / RAG metrics).
    rationales: Dict[str, str] = Field(default_factory=dict)


class ConfusionMatrix(BaseModel):
    """Full right/wrong breakdown per class — what you actually look at to debug
    a classification task (doc §3.3). `matrix[i][j]` = cases whose true label is
    `labels[i]` and predicted label is `labels[j]`; the diagonal is correct."""

    labels: List[str]
    matrix: List[List[int]]


class OperationalSummary(BaseModel):
    """Aggregate operational metrics across a run's LLM calls (doc §3.6).
    The tail matters for UX, so we report p95 alongside the median."""

    calls: int
    latency_p50_ms: float
    latency_p95_ms: float
    tokens_in: int
    tokens_out: int
    cost: float


class RunResponse(BaseModel):
    run_id: str
    created_at: str
    dataset_name: Optional[str] = None
    metrics: List[str]
    per_case: List[CaseResult]
    aggregate: Dict[str, Optional[float]]
    # Present only when a classification metric was run.
    confusion_matrix: Optional[ConfusionMatrix] = None
    # Present only when an LLM-judged metric ran (judge calls cost money/time).
    operational: Optional[OperationalSummary] = None


class RunSummary(BaseModel):
    """A run, minus the per-case detail — for the history list and comparisons."""

    run_id: str
    created_at: str
    dataset_name: Optional[str] = None
    metrics: List[str]
    aggregate: Dict[str, Optional[float]]


class ModelInfo(BaseModel):
    id: str
    name: str


class GenerateRequest(BaseModel):
    """Call an LLM live to produce outputs for the dataset (doc §5.3)."""

    cases: List[TestCase]
    model: Optional[str] = None
    system: Optional[str] = None
    max_tokens: int = 1024


class GeneratedCase(BaseModel):
    id: str
    prediction: str
    operational: Operational


class GenerateResponse(BaseModel):
    model: str
    cases: List[GeneratedCase]
    summary: OperationalSummary


# --- dimensionality-reduction explorer (doc: Explorer feature) --------------


class ProjectionParamSpec(BaseModel):
    """One tunable knob for a DR algorithm — drives a labelled slider in the UI."""

    key: str
    label: str
    kind: str  # "int" | "float"
    default: float
    min: float
    max: float
    step: float
    help: str


class ProjectionAlgorithmInfo(BaseModel):
    """Self-describing DR algorithm for the picker (mirrors MetricInfo's role)."""

    id: str  # pca | tsne | umap
    name: str
    description: str
    params: List[ProjectionParamSpec] = Field(default_factory=list)
    available: bool = True
    unavailable_reason: Optional[str] = None


class SampleDatasetInfo(BaseModel):
    """A built-in high-dimensional dataset to practice DR on."""

    id: str
    name: str
    description: str
    n_samples: int
    n_features: int


class ProjectRequest(BaseModel):
    """Project vectors to 2-D. `source` picks where the vectors come from."""

    source: str  # "dataset" (embed case text) | "sample" (built-in dataset)
    algorithms: List[str]  # e.g. ["pca", "tsne", "umap"]
    # source="dataset": which case field to embed, plus the cases.
    field: Optional[str] = None  # input | prediction | reference | context
    cases: List[TestCase] = Field(default_factory=list)
    # source="sample": which built-in dataset.
    sample_id: Optional[str] = None
    # Per-algorithm params, e.g. {"tsne": {"perplexity": 30}}.
    params: Dict[str, Dict[str, float]] = Field(default_factory=dict)


class ProjectedPoint(BaseModel):
    id: str
    x: float
    y: float
    label: Optional[str] = None  # category for coloring (digit, species, ref label)
    text: Optional[str] = None  # short preview for the hover tooltip


class ProjectionMeta(BaseModel):
    """Teaching signals from one reduction — all optional, algorithm-dependent."""

    variance_explained: Optional[List[float]] = None  # PCA: ratio per component
    perplexity: Optional[int] = None  # t-SNE (after clamping to data size)
    n_neighbors: Optional[int] = None  # UMAP
    min_dist: Optional[float] = None  # UMAP
    preprocessed_dims: Optional[int] = None  # PCA-preprocess dims before t-SNE/UMAP


class ProjectionResult(BaseModel):
    algorithm: str
    points: List[ProjectedPoint]
    meta: ProjectionMeta = Field(default_factory=ProjectionMeta)


class ProjectResponse(BaseModel):
    source: str
    n_points: int
    dims_in: int
    label_kind: str  # "category" | "none"
    results: List[ProjectionResult]
