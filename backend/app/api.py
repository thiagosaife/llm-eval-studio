"""API layer: endpoints, validation, and the scoring loop (doc §5.3).

The scoring loop is the only place that knows the cross-cutting rules — which
inputs a metric needs, how to summarise it, and how to build a confusion matrix.
Metrics themselves just compute.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException

from . import storage
from .metrics import registry
from .metrics.base import BaseMetric, Scored
from .metrics.exact_match import normalize
from .models import (
    CaseResult,
    ConfusionMatrix,
    Dataset,
    DatasetCreate,
    EvaluateRequest,
    MetricInfo,
    RunResponse,
    TestCase,
)

router = APIRouter()


@router.get("/metrics", response_model=List[MetricInfo])
def list_metrics() -> List[MetricInfo]:
    """Drive the metric picker and the inline teaching notes (doc §6.2)."""
    return registry.all_infos()


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


@router.post("/evaluate", response_model=RunResponse)
def evaluate(request: EvaluateRequest) -> RunResponse:
    """The main call: score every case with the selected metrics (doc §5.5)."""
    if not request.metrics:
        raise HTTPException(status_code=400, detail="Select at least one metric.")
    if not request.cases:
        raise HTTPException(status_code=400, detail="Provide at least one case.")

    selected = _resolve_metrics(request.metrics)

    per_case: List[CaseResult] = []
    for case in request.cases:
        scores: Dict[str, Optional[float]] = {
            metric.info.id: _score_case(metric, case) for metric in selected
        }
        per_case.append(
            CaseResult(
                id=case.id,
                input=case.input,
                prediction=case.prediction,
                reference=case.reference,
                context=case.context,
                scores=scores,
            )
        )

    aggregate: Dict[str, Optional[float]] = {}
    for metric in selected:
        mid = metric.info.id
        scored = [
            Scored(c.prediction, c.reference, c.context, c.scores[mid]) for c in per_case
        ]
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
    )
    storage.save_run(run)
    return run


@router.get("/runs/{run_id}", response_model=RunResponse)
def get_run(run_id: str) -> RunResponse:
    """Retrieve a stored run for the dashboard / comparisons (doc §5.3)."""
    run = storage.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return run


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


def _score_case(metric: BaseMetric, case: TestCase) -> Optional[float]:
    """Score one case with one metric, or return None if not applicable.

    `None` (rendered as a dash) is different from 0.0: the metric was never run
    because the case lacked an input it required, or the metric is set-level.
    """
    if metric.info.aggregate_only:
        return None
    if not case.prediction:
        return None
    if metric.info.requires_reference and not case.reference:
        return None
    return round(metric.score(case.prediction, case.reference, case.context), 4)


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
