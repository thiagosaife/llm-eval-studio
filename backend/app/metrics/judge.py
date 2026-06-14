"""Model-based metrics: LLM-as-a-judge and the RAG triad (doc §3.4, §3.5).

These are the most practical metrics for open-ended generation — a strong model
grades against a rubric and explains itself. They all flow through `llm.judge`,
which prompts for a strict `{"score": 1-5, "rationale": "..."}` reply and
normalizes the score to 0–1. Each metric below differs only in its rubric.

`requires_llm = True` tells the engine to call `judge()` (which returns a
rationale + the call's cost) instead of `score()`.
"""
from __future__ import annotations

from typing import Optional, Tuple

from .. import llm
from ..models import JudgeConfig, MetricInfo, TestCase
from .base import BaseMetric, MetricOutput

_JUDGE_SYSTEM = (
    "You are a meticulous evaluator of AI-generated answers. "
    "Grade strictly against the provided criterion. "
    'Respond with ONLY a single JSON object: {"score": <integer 1-5>, '
    '"rationale": "<one or two sentences explaining the score>"}. '
    "5 means it fully satisfies the criterion; 1 means it fails it."
)


def _field(label: str, value: Optional[str]) -> str:
    return f"{label}:\n{(value or '').strip() or '(none)'}\n\n"


class _LLMMetric(BaseMetric):
    requires_llm = True
    # Any provider satisfies an LLM metric — availability is decided per-run from
    # the chosen judge model's provider, not a single SDK module here.
    requires_modules = ()
    install_hint = "add an API key for any provider"

    # Never called — the engine routes LLM metrics through judge() — but the
    # ABC requires a concrete score().
    def score(self, prediction, reference=None, context=None) -> float:  # type: ignore[override]
        raise NotImplementedError

    def _inputs(self, case: TestCase, config: Optional[JudgeConfig]) -> Tuple[str, str]:
        """Build this metric's (criterion, prompt_body) for a case. Overridden."""
        raise NotImplementedError

    def _build(self, criterion: str, prompt_body: str) -> Tuple[str, str]:
        """The exact (system, user_prompt) a judge call sends."""
        return _JUDGE_SYSTEM, f"Criterion: {criterion}\n\n{prompt_body}Now grade it."

    def preview_prompt(self, case: TestCase, config: Optional[JudgeConfig]) -> Tuple[str, str]:
        """Reproduce (system, prompt) for a case WITHOUT calling the model.

        The cost estimator uses this so its projection matches the real run's
        prompt exactly — same single source of truth as judge() below.
        """
        criterion, prompt_body = self._inputs(case, config)
        return self._build(criterion, prompt_body)

    def judge(self, case: TestCase, config: Optional[JudgeConfig]) -> MetricOutput:
        model = (config.model if config and config.model else None) or llm.DEFAULT_MODEL
        api_key = llm.key_for(model, config.keys if config else None)
        system, prompt = self.preview_prompt(case, config)
        judgment = llm.judge(system, prompt, model=model, api_key=api_key)
        return MetricOutput(
            value=judgment.score, rationale=judgment.rationale, completion=judgment.completion
        )


class LLMJudge(_LLMMetric):
    info = MetricInfo(
        id="llm_judge",
        name="LLM-as-a-judge",
        family="model_judge",
        description="A strong model (Claude, GPT, or Gemini) grades the output against your rubric and explains why.",
        requires_reference=False,
        range=[0.0, 1.0],
        how_to_read="The most practical metric for open-ended generation; closest to human judgment.",
        caveat="Has biases (verbosity, position, self-preference). Spot-check against human labels.",
        produces_rationale=True,
    )
    DEFAULT_RUBRIC = "Rate the overall correctness, relevance, and quality of the answer."

    def _inputs(self, case: TestCase, config: Optional[JudgeConfig]) -> Tuple[str, str]:
        rubric = (config.rubric if config and config.rubric else None) or self.DEFAULT_RUBRIC
        body = _field("Question / instruction", case.input)
        if case.reference:
            body += _field("Reference (ideal) answer", case.reference)
        body += _field("Answer to grade", case.prediction)
        return rubric, body


class Faithfulness(_LLMMetric):
    info = MetricInfo(
        id="faithfulness",
        name="Faithfulness",
        family="rag",
        description="Does the answer stick to the retrieved context, or did it hallucinate?",
        requires_reference=False,
        requires_context=True,
        range=[0.0, 1.0],
        how_to_read="High = every claim is grounded in the context. A generation-quality signal.",
        caveat="A faithful answer can still be unhelpful — pair it with answer relevancy.",
        produces_rationale=True,
    )

    def _inputs(self, case: TestCase, config: Optional[JudgeConfig]) -> Tuple[str, str]:
        criterion = (
            "Is every claim in the answer supported by the retrieved context? "
            "Penalize anything stated that the context does not support (hallucination)."
        )
        body = _field("Retrieved context", case.context) + _field("Answer", case.prediction)
        return criterion, body


class AnswerRelevancy(_LLMMetric):
    info = MetricInfo(
        id="answer_relevancy",
        name="Answer relevancy",
        family="rag",
        description="Does the answer actually address the question that was asked?",
        requires_reference=False,
        range=[0.0, 1.0],
        how_to_read="High = on-topic and complete for the question. Also a generation signal.",
        caveat="Relevant ≠ correct or grounded — read it next to faithfulness.",
        produces_rationale=True,
    )

    def _inputs(self, case: TestCase, config: Optional[JudgeConfig]) -> Tuple[str, str]:
        criterion = (
            "Does the answer directly and completely address the question asked? "
            "Penalize evasive, partial, or off-topic answers."
        )
        body = _field("Question", case.input) + _field("Answer", case.prediction)
        return criterion, body


class ContextRelevancy(_LLMMetric):
    info = MetricInfo(
        id="context_relevancy",
        name="Context relevancy",
        family="rag",
        description="Did the retriever fetch context that's actually relevant to the question?",
        requires_reference=False,
        requires_context=True,
        range=[0.0, 1.0],
        how_to_read="Low here means a *retrieval* problem, not a generation one.",
        caveat="Measures the retriever, not the answer — separates the two failure modes.",
        produces_rationale=True,
    )

    def _inputs(self, case: TestCase, config: Optional[JudgeConfig]) -> Tuple[str, str]:
        criterion = (
            "Does the retrieved context contain the information needed to answer the question? "
            "Penalize context that is off-topic or missing the key facts."
        )
        body = _field("Question", case.input) + _field("Retrieved context", case.context)
        return criterion, body
