"""API layer: endpoints, validation, and the scoring loop (doc §5.3).

The scoring loop is the only place that knows the cross-cutting rules — which
inputs a metric needs, how to summarise it, how to build a confusion matrix, and
how to route LLM-judged metrics through `judge()` (which also yields a rationale
and the cost of the call). Metrics themselves just compute.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException

from . import embeddings_util, llm, projection, storage
from .llm import Completion
from .metrics import registry
from .metrics.base import BaseMetric, Scored
from .metrics.exact_match import normalize
from .models import (
    CaseResult,
    ConfusionMatrix,
    Dataset,
    DatasetCreate,
    EstimateRequest,
    EstimateResponse,
    EvaluateRequest,
    GeneratedCase,
    GenerateRequest,
    GenerateResponse,
    JudgeConfig,
    MetricEstimate,
    MetricInfo,
    ModelInfo,
    Operational,
    OperationalSummary,
    ProjectedPoint,
    ProjectionAlgorithmInfo,
    ProjectionMeta,
    ProjectionResult,
    ProjectRequest,
    ProjectResponse,
    RunResponse,
    RunSummary,
    SampleDatasetInfo,
    TestCase,
)

router = APIRouter()


@router.get("/metrics", response_model=List[MetricInfo])
def list_metrics() -> List[MetricInfo]:
    """Drive the metric picker and the inline teaching notes (doc §6.2)."""
    return registry.all_infos()


@router.get("/models", response_model=List[ModelInfo])
def list_models() -> List[ModelInfo]:
    """Selectable generation/judge models for the run config (doc §6.1)."""
    return [ModelInfo(id=mid, name=name) for mid, name in llm.MODELS]


@router.post("/datasets", response_model=Dataset, status_code=201)
def create_dataset(payload: DatasetCreate) -> Dataset:
    dataset = Dataset(id=f"ds-{uuid.uuid4().hex[:8]}", name=payload.name, cases=payload.cases)
    storage.save_dataset(dataset)
    return dataset


@router.get("/datasets/{dataset_id}", response_model=Dataset)
def get_dataset(dataset_id: str) -> Dataset:
    dataset = storage.get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found")
    return dataset


@router.post("/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest) -> GenerateResponse:
    """Call an LLM live to produce predictions for the dataset (doc §5.3, §8.3)."""
    if not llm.available():
        raise HTTPException(status_code=400, detail=llm.unavailable_reason())
    prompts = [c for c in request.cases if (c.input or "").strip()]
    if not prompts:
        raise HTTPException(status_code=400, detail="No cases have an input to generate from.")

    model = request.model or llm.DEFAULT_MODEL
    generated: List[GeneratedCase] = []
    completions: List[Completion] = []
    try:
        for case in prompts:
            completion = llm.complete(
                case.input or "", model=model, system=request.system, max_tokens=request.max_tokens
            )
            completions.append(completion)
            generated.append(
                GeneratedCase(id=case.id, prediction=completion.text, operational=_op(completion))
            )
    except Exception as exc:  # surface provider/auth errors cleanly
        raise HTTPException(status_code=502, detail=f"Generation failed: {exc}") from exc

    return GenerateResponse(model=model, cases=generated, summary=_operational_summary(completions))


@router.post("/evaluate", response_model=RunResponse)
def evaluate(request: EvaluateRequest) -> RunResponse:
    """The main call: score every case with the selected metrics (doc §5.5)."""
    if not request.metrics:
        raise HTTPException(status_code=400, detail="Select at least one metric.")
    if not request.cases:
        raise HTTPException(status_code=400, detail="Provide at least one case.")

    selected = _resolve_metrics(request.metrics)
    completions: List[Completion] = []  # every judge call, for the operational summary

    per_case: List[CaseResult] = []
    for case in request.cases:
        scores: Dict[str, Optional[float]] = {}
        rationales: Dict[str, str] = {}
        for metric in selected:
            value, rationale, completion = _evaluate_metric(metric, case, request.judge)
            scores[metric.info.id] = value
            if rationale:
                rationales[metric.info.id] = rationale
            if completion is not None:
                completions.append(completion)
        per_case.append(
            CaseResult(
                id=case.id,
                input=case.input,
                prediction=case.prediction,
                reference=case.reference,
                context=case.context,
                scores=scores,
                rationales=rationales,
            )
        )

    aggregate: Dict[str, Optional[float]] = {}
    for metric in selected:
        mid = metric.info.id
        scored = [Scored(c.prediction, c.reference, c.context, c.scores[mid]) for c in per_case]
        aggregate[mid] = metric.aggregate(scored)

    confusion = None
    if any(m.info.family == "classification" for m in selected):
        confusion = _confusion_matrix(request.cases)

    run = RunResponse(
        run_id=f"run-{uuid.uuid4().hex[:10]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        dataset_name=request.dataset_name,
        metrics=[m.info.id for m in selected],
        per_case=per_case,
        aggregate=aggregate,
        confusion_matrix=confusion,
        operational=_operational_summary(completions) if completions else None,
    )
    storage.save_run(run)
    return run


@router.post("/estimate", response_model=EstimateResponse)
def estimate(request: EstimateRequest) -> EstimateResponse:
    """Project a run's tokens and cost before any billable call (doc §3.6).

    Only LLM-judged metrics cost money; everything else is local and free. Input
    tokens are exact when `exact` is set and a key is present (via the free
    `count_tokens` endpoint), otherwise an offline heuristic — so an estimate is
    available even before a key exists. Output tokens can't be known in advance,
    so we report an expected size and a worst-case ceiling."""
    metrics = _resolve_metrics_lenient(request.metrics)
    model = (request.judge.model if request.judge and request.judge.model else None) or llm.DEFAULT_MODEL
    exact = bool(request.exact and llm.available())

    per_metric: List[MetricEstimate] = []
    total_calls = 0
    total_tokens_in = 0
    for metric in metrics:
        if not metric.requires_llm:
            continue  # local metrics make no API calls
        calls = 0
        tokens_in = 0
        for case in request.cases:
            if not _applicable(metric, case):
                continue
            system, prompt = metric.preview_prompt(case, request.judge)
            if exact:
                try:
                    n = llm.count_input_tokens(model, system, prompt)
                except Exception:
                    exact = False  # provider/auth hiccup — finish with the heuristic
                    n = llm.estimate_input_tokens(system, prompt)
            else:
                n = llm.estimate_input_tokens(system, prompt)
            calls += 1
            tokens_in += n
        if calls:
            per_metric.append(
                MetricEstimate(metric_id=metric.info.id, calls=calls, tokens_in=tokens_in)
            )
            total_calls += calls
            total_tokens_in += tokens_in

    expected_out = total_calls * llm.JUDGE_OUTPUT_TOKENS_EST
    max_out = total_calls * llm.JUDGE_MAX_TOKENS
    return EstimateResponse(
        model=model,
        llm_calls=total_calls,
        tokens_in=total_tokens_in,
        expected_tokens_out=expected_out,
        max_tokens_out=max_out,
        expected_cost=llm.cost(model, total_tokens_in, expected_out),
        max_cost=llm.cost(model, total_tokens_in, max_out),
        exact=exact and total_calls > 0,
        per_metric=per_metric,
    )


@router.get("/runs", response_model=List[RunSummary])
def list_runs() -> List[RunSummary]:
    """Recent runs for the history list and run-vs-run comparison (doc §6.2)."""
    return storage.list_runs()


@router.get("/runs/{run_id}", response_model=RunResponse)
def get_run(run_id: str) -> RunResponse:
    """Retrieve a stored run for the dashboard / comparisons (doc §5.3)."""
    run = storage.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return run


# --- dimensionality-reduction explorer --------------------------------------


@router.get("/projection/algorithms", response_model=List[ProjectionAlgorithmInfo])
def list_projection_algorithms() -> List[ProjectionAlgorithmInfo]:
    """DR algorithms + availability — drives the Explorer's picker (mirrors /metrics)."""
    return [ProjectionAlgorithmInfo(**a) for a in projection.algorithm_infos()]


@router.get("/projection/samples", response_model=List[SampleDatasetInfo])
def list_projection_samples() -> List[SampleDatasetInfo]:
    """Built-in high-dimensional datasets to practice DR on."""
    return [SampleDatasetInfo(**s) for s in projection.sample_infos()]


_FIELDS = ("input", "prediction", "reference", "context")


@router.post("/project", response_model=ProjectResponse)
def project(request: ProjectRequest) -> ProjectResponse:
    """Embed (or load) vectors and project them to 2-D with each chosen algorithm."""
    if not request.algorithms:
        raise HTTPException(status_code=400, detail="Select at least one algorithm.")
    for algo in request.algorithms:
        if not projection.is_available(algo):
            raise HTTPException(status_code=400, detail=f"Algorithm '{algo}' is unavailable.")

    if request.source == "sample":
        ids, vectors, labels, texts, label_kind = _sample_source(request)
    elif request.source == "dataset":
        ids, vectors, labels, texts, label_kind = _dataset_source(request)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown source '{request.source}'.")

    results: List[ProjectionResult] = []
    for algo in request.algorithms:
        try:
            coords, meta = projection.reduce(vectors, algo, request.params.get(algo, {}))
        except Exception as exc:  # surface a clean message instead of a 500 traceback
            raise HTTPException(status_code=500, detail=f"Projection failed ({algo}): {exc}") from exc
        points = [
            ProjectedPoint(
                id=ids[i],
                x=round(float(coords[i][0]), 4),
                y=round(float(coords[i][1]), 4),
                label=labels[i] if labels else None,
                text=texts[i] if texts else None,
            )
            for i in range(len(ids))
        ]
        results.append(ProjectionResult(algorithm=algo, points=points, meta=ProjectionMeta(**meta)))

    return ProjectResponse(
        source=request.source,
        n_points=len(ids),
        dims_in=int(vectors.shape[1]),
        label_kind=label_kind,
        results=results,
    )


def _sample_source(request: ProjectRequest):
    if not request.sample_id:
        raise HTTPException(status_code=400, detail="Choose a sample dataset.")
    try:
        vectors, labels, _ = projection.load_sample(request.sample_id)
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Unknown sample '{request.sample_id}'.")
    ids = [str(i) for i in range(len(labels))]
    return ids, vectors, labels, None, "category"


def _dataset_source(request: ProjectRequest):
    if not embeddings_util.available():
        raise HTTPException(status_code=400, detail=embeddings_util.unavailable_reason())
    field = request.field or "prediction"
    if field not in _FIELDS:
        raise HTTPException(status_code=400, detail=f"Field must be one of {_FIELDS}.")

    rows = [(c, (getattr(c, field) or "").strip()) for c in request.cases]
    rows = [(c, text) for c, text in rows if text]
    if len(rows) < 3:
        raise HTTPException(
            status_code=400,
            detail=f"Need at least 3 cases with a non-empty '{field}' to project.",
        )

    ids = [c.id for c, _ in rows]
    texts_full = [text for _, text in rows]
    vectors = embeddings_util.embed_texts(texts_full)

    # Color by the reference when it looks categorical (a few short, repeated
    # labels); for free-form references coloring would be noise, so skip it.
    refs = [(c.reference or "").strip() for c, _ in rows]
    if _looks_categorical(refs):
        labels = refs
        label_kind = "category"
    else:
        labels = None
        label_kind = "none"

    previews = [t if len(t) <= 80 else t[:77] + "…" for t in texts_full]
    return ids, vectors, labels, previews, label_kind


def _looks_categorical(values: List[str]) -> bool:
    """A reference column is a class label if every row has one, the values are
    short, and there are only a handful of distinct ones."""
    if not values or any(not v for v in values):
        return False
    distinct = set(values)
    return 2 <= len(distinct) <= min(12, len(values) - 1) and all(len(v) <= 40 for v in values)


# --- internals --------------------------------------------------------------


def _resolve_metrics(metric_ids: List[str]) -> List[BaseMetric]:
    resolved: List[BaseMetric] = []
    for metric_id in metric_ids:
        metric = registry.get(metric_id)
        if metric is None:
            raise HTTPException(status_code=400, detail=f"Unknown metric '{metric_id}'.")
        if not metric.info.available:
            raise HTTPException(
                status_code=400,
                detail=f"Metric '{metric_id}' is unavailable: {metric.info.unavailable_reason}",
            )
        resolved.append(metric)
    return resolved


def _resolve_metrics_lenient(metric_ids: List[str]) -> List[BaseMetric]:
    """Like `_resolve_metrics`, but does NOT require availability — a key-gated
    LLM metric is fine to *estimate* even when it can't yet be run. Unknown ids
    still 400."""
    resolved: List[BaseMetric] = []
    for metric_id in metric_ids:
        metric = registry.get(metric_id)
        if metric is None:
            raise HTTPException(status_code=400, detail=f"Unknown metric '{metric_id}'.")
        resolved.append(metric)
    return resolved


def _evaluate_metric(
    metric: BaseMetric, case: TestCase, judge_config: Optional[JudgeConfig]
) -> Tuple[Optional[float], Optional[str], Optional[Completion]]:
    """Score one case with one metric. Returns (value, rationale, completion).

    `value=None` means not-applicable (rendered as a dash). LLM metrics also
    carry a rationale and the completion (for the operational summary)."""
    if not _applicable(metric, case):
        return None, None, None

    if metric.requires_llm:
        try:
            out = metric.judge(case, judge_config)
        except Exception as exc:  # one bad judge call shouldn't sink the run
            return None, f"Judge error: {exc}", None
        return out.value, out.rationale, out.completion

    if metric.info.aggregate_only:  # set-level only (precision/recall/F1)
        return None, None, None
    value = round(metric.score(case.prediction or "", case.reference, case.context), 4)
    return value, None, None


def _applicable(metric: BaseMetric, case: TestCase) -> bool:
    if not (case.prediction or "").strip():
        return False
    if metric.info.requires_reference and not (case.reference or "").strip():
        return False
    if metric.info.requires_context and not (case.context or "").strip():
        return False
    return True


def _op(c: Completion) -> Operational:
    return Operational(
        latency_ms=c.latency_ms, tokens_in=c.tokens_in, tokens_out=c.tokens_out, cost=c.cost
    )


def _percentile(sorted_values: List[float], pct: float) -> float:
    """Nearest-rank percentile of an already-sorted list."""
    if not sorted_values:
        return 0.0
    rank = max(0, min(len(sorted_values) - 1, round(pct / 100 * (len(sorted_values) - 1))))
    return sorted_values[rank]


def _operational_summary(completions: List[Completion]) -> OperationalSummary:
    latencies = sorted(c.latency_ms for c in completions)
    return OperationalSummary(
        calls=len(completions),
        latency_p50_ms=_percentile(latencies, 50),
        latency_p95_ms=_percentile(latencies, 95),
        tokens_in=sum(c.tokens_in for c in completions),
        tokens_out=sum(c.tokens_out for c in completions),
        cost=round(sum(c.cost for c in completions), 6),
    )


def _confusion_matrix(cases: List[TestCase]) -> Optional[ConfusionMatrix]:
    """Right/wrong breakdown over cases that have both a prediction and a
    reference label (doc §3.3). Labels are normalized the same way Exact Match
    normalizes, so the matrix agrees with the per-case correctness."""
    pairs = [
        (normalize(c.reference), normalize(c.prediction))
        for c in cases
        if c.prediction and c.reference
    ]
    if not pairs:
        return None
    labels = sorted({label for pair in pairs for label in pair})
    index = {label: i for i, label in enumerate(labels)}
    matrix = [[0 for _ in labels] for _ in labels]
    for true_label, pred_label in pairs:
        matrix[index[true_label]][index[pred_label]] += 1
    return ConfusionMatrix(labels=labels, matrix=matrix)
