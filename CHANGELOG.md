# Changelog

All notable changes to **LLM Eval Studio**. The project was built in three
phases following [the design doc](./docs/llm-eval-studio.md) §9 — each phase
ships something demonstrable, with the heavy dependencies arriving only once the
architecture is proven.

The format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## Phase 3 — "Make it impressive" — 2026-06-13

### Added

- **Live generation** from a Claude model — pick the model, system prompt, and
  max tokens, and produce predictions for the dataset (`POST /api/generate`).
- **LLM-as-a-judge** metric (`model_judge` family): a configurable rubric, a
  1–5 grade normalized to 0–1, and a **written rationale** surfaced per case in
  the inspector.
- **RAG triad** (LLM-judged): faithfulness, answer relevancy, and context
  relevancy. Faithfulness and context relevancy require retrieved `context`.
- **Operational metrics** — p50/p95 latency, tokens in/out, and cost across a
  run's model calls, shown next to the quality cards (`§3.6`).
- **Score-distribution histogram** and **run-vs-run comparison** on the results
  dashboard (the "did I actually improve?" loop, `§8.6`).
- Endpoints: `POST /api/generate`, `GET /api/models`, `GET /api/runs`.
- Engine: a third metric seam, `judge()`, returning score + rationale + the
  call's cost; new `MetricInfo` flags `requires_context` and `produces_rationale`.
- Backend dependency: `anthropic` (default model `claude-opus-4-8`). The
  LLM features (generation, judge, RAG) are gated on `ANTHROPIC_API_KEY` and
  greyed out in the picker without it.
- Tests use a throwaway DB via the `LLM_EVAL_DB` override; LLM paths are covered
  with a mocked provider.

## Phase 2 — "Make it useful" — 2026-06-13

### Added

- **Classification metrics** (scikit-learn): Accuracy + macro Precision / Recall
  / F1, plus a **confusion matrix**. Precision/Recall/F1 are set-level — shown as
  summary cards, omitted from the per-case table.
- **Semantic metrics**: Cosine similarity (sentence-transformers) and BERTScore.
  Heavy libraries load lazily; models download on first use.
- **CSV import** with a column → field mapping UI (papaparse); JSON import.
- **Case inspector word-level diff** (replacing the shared-word highlight).
- **SQLite persistence** — runs and datasets survive a server restart.
- Engine: an `aggregate()` seam (default mean; set-level metrics override it);
  new `MetricInfo` flags `available` and `aggregate_only`; availability detection
  so metrics whose libraries aren't installed are greyed out.

## Phase 1 — "Skeleton" — 2026-06-13

### Added

- Three views (`/datasets`, `/run`, `/results/:runId`) and a typed API client
  mirroring the backend's Pydantic models.
- The **metric registry engine** ("write one class, register it"), with
  **Exact Match** and **ROUGE-1 / ROUGE-2 / ROUGE-L** in pure Python.
- A **metric picker** with inline teaching notes ("read it" / "it lies when…")
  that greys out reference-based metrics until a gold answer exists.
- A results dashboard: aggregate **summary cards**, a per-case **table** sortable
  by any metric (defaults to worst-first), and a side-by-side **case inspector**.
- Endpoints: `GET /api/metrics`, `POST /api/evaluate`, `POST`/`GET /api/datasets`,
  `GET /api/runs/{id}`. Three Pinia stores (dataset, run, metricsCatalog).
