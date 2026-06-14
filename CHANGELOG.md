# Changelog

All notable changes to **LLM Eval Studio**. The project was built in three
phases following [the design doc](./docs/llm-eval-studio.md) §9 — each phase
ships something demonstrable, with the heavy dependencies arriving only once the
architecture is proven.

The format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## Unreleased

### Added

- **Pre-run cost & token estimator** — projects a run's cost *before* any billable
  call, so you know what an LLM-judge run will cost before spending a cent. A new
  **Cost estimate** card on the Run page shows the expected cost, a worst-case
  ceiling (every judge reply hitting the token cap), the LLM call count, and input
  tokens. It updates live as you pick metrics/cases using an offline heuristic (no
  API key needed); a **Get exact count** button (🎯) swaps in exact input tokens
  via Anthropic's `count_tokens` endpoint, which is **free** (it doesn't run the
  model). A per-run **spend cap** (persisted) triggers a confirmation before a run
  whose worst-case cost exceeds it.
  - Backend: `POST /api/estimate` (`backend/app/api.py`); `estimate_input_tokens`
    / `count_input_tokens` / `cost` + the `JUDGE_MAX_TOKENS` / `JUDGE_OUTPUT_TOKENS_EST`
    constants in `backend/app/llm.py`; judge metrics expose `preview_prompt()` so
    the estimate uses the identical prompt the real run sends. Only LLM-judge
    metrics are billable; local metrics estimate as free.
  - Frontend: `EstimateCard.vue`, an `estimate` action + `spendCap` in the run
    store, and a confirm gate in `RunControls.vue`.
  - LLM-judge metrics are now **selectable for an estimate even without an API
    key** (they show a "needs key to run" badge); the run itself stays gated on the
    key. New `MetricInfo.estimable` flag distinguishes "no key yet" (estimable)
    from "SDK not installed" (not estimable).
  - A `!` tip on the estimate card opens a new **"What costs money"** entry in the
    guide: only LLM-judge and RAG metrics cost money (they call Claude once per
    case); lexical, classification, and semantic metrics run locally and are free;
    and scoring vs. live generation are separate billable steps.
- **Scrollable results table** — the per-case table is now a fixed-height scroll
  region (sticky header) with affordances that make it obvious there's more to
  inspect: an always-visible scrollbar (macOS overlay scrollbars stay hidden
  otherwise), soft edge fades, and up/down/left/right arrow buttons that appear
  only when there's more content that way (`ResultsTable.vue`).
- **Backend loads `backend/.env` at startup** (`python-dotenv`, in `app/main.py`),
  so `uvicorn app.main:app` picks up `ANTHROPIC_API_KEY` without `--env-file`.
- **Embedding & dimensionality-reduction explorer** (`/explore`, **🔭 Explore** in
  the top bar): project high-dimensional vectors to 2-D and compare **PCA / t-SNE
  / UMAP** side-by-side with live params (perplexity, n_neighbors, min_dist). Two
  data sources — your dataset's embeddings (a semantic map of cases, colored by a
  categorical reference) and built-in sklearn demos (digits, iris). A teaching
  feature: swap algorithms to *see* how each lays the same data out.
  - Backend: `backend/app/projection.py` (DR engine + sample datasets) and
    `backend/app/embeddings_util.py` (shared embedder, also used by Cosine);
    endpoints `GET /api/projection/algorithms`, `GET /api/projection/samples`,
    `POST /api/project`. PCA/t-SNE need no new deps; **UMAP adds `umap-learn`**
    and is greyed out when absent.
  - Frontend: `ExploreView.vue` + hand-rolled SVG `ScatterPlot.vue`, a
    `projection` Pinia store, and DR teaching content (a "Dimensionality
    reduction" guide section + glossary terms) in `metricGuide.ts`.
- **Metrics & concepts guide** — a new `/guide` reference route explaining every
  metric (what it measures, how it's computed, a worked example, when to use it,
  and where it misleads), a **glossary** of the underlying concepts, and
  **further-reading** links to the primary sources.
- **Info tips (`!`)** throughout the app, making it self-teaching: each metric in
  the Run picker now has a `!` button with a hover summary that links to its full
  entry in the guide (opens in a new tab). The metric-specific teaching content
  lives in `frontend/src/content/metricGuide.ts`.
- **Per-field explanations** in the Dataset editor — Input, Prediction,
  Reference, and Context each gained a `!` tip whose hover text is the glossary
  definition and whose link opens that glossary entry.
- Reusable **`InfoTip.vue`** component (hover/focus bubble, optional new-tab
  link) and a **"Metrics guide" toggle** in the top bar — it opens the guide and,
  when you're already on it, returns you to the page you came from. Router
  `scrollBehavior` now honors `#metric-…` / `#term-…` anchors.

### Changed

- Widened the app shell (1120 → 1200px) so the metric picker's two-line titles
  have room to breathe.

### Fixed

- **`!` tip alignment** — the tip now keeps a consistent margin from its text and
  rides the text's vertical middle.
- **Metric checkbox no longer deforms** when a card's title wraps to two lines
  (the checkbox is fixed-size; the title shrinks/wraps instead).
- **Prediction / Reference textareas now line up** in the Dataset editor — their
  labels share a fixed-height band, so the taller "gold answer" badge on
  Reference no longer pushes its field lower than Prediction's.

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
