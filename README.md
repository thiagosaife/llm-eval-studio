# LLM Eval Studio

A browser-based tool that teaches developers how to evaluate Large Language
Model (LLM) outputs and computes the metrics for them. This repo implements
**all three phases** of [the design doc](./docs/llm-eval-studio.md): the working
`dataset → score → display` loop, extended with classification + embedding
metrics, import/persistence, and live generation + LLM-as-a-judge + RAG +
operational metrics + run comparison.

- **Backend** — Python / FastAPI; lexical, classification, embedding, and
  model-based (judge / RAG / generation) metrics via Anthropic, OpenAI, or Gemini.
- **Frontend** — Vue 3 + TypeScript (Vite, Pinia, Vue Router).
- **Self-teaching** — a built-in [metrics guide](#learn-as-you-go) explains every
  metric and the concepts behind them, and `!` tips throughout the app link
  straight to the relevant entry.

See [CHANGELOG.md](./CHANGELOG.md) for the full feature set, broken down by phase.

## Architecture

The metric engine is a registry (`backend/app/metrics/`): adding a metric is
"write one class, register it," and it appears in the UI automatically. Each
metric exposes a `score()` (per-case) and an `aggregate()` hook (set-level
metrics like precision override it); LLM-judged metrics implement `judge()`
instead, returning a score + rationale + the call's cost. The frontend mirrors
the backend's Pydantic models in `frontend/src/api/types.ts`, keeping the app
type-safe end to end.

## Run it

Two terminals.

**1. Backend** (http://localhost:8000, docs at `/docs`):

```bash
cd backend
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt   # Phase 2 pulls in PyTorch — sizeable
./.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

> The embedding metrics (cosine, BERTScore) download their models on **first
> use** (~0.5 GB total), so the first run that selects them is slow; later runs
> are fast. The server boots instantly regardless — nothing heavy loads at
> startup, and unavailable metrics are simply greyed out in the picker.
>
> **For live generation + LLM-judge + RAG metrics**, provide an API key for any
> of the three providers — **Anthropic** (`ANTHROPIC_API_KEY`), **OpenAI**
> (`OPENAI_API_KEY`), or **Google Gemini** (`GEMINI_API_KEY`). Drop keys in
> `backend/.env` (auto-loaded at startup — no `--env-file` needed), or enter them
> per-provider on the in-app **⚙️ Settings** page (stored in the browser, sent with
> each run, never persisted server-side). Generation and the judge each pick their
> own provider+model; a model whose provider has no key is greyed out. The default
> model is `claude-opus-4-8`. Without any key, those features are greyed out and
> everything else still works; the pre-run **cost estimate** still works with no key
> (offline heuristic), and "Get exact count" uses each provider's exact counting
> (local `tiktoken` for OpenAI; the free `count_tokens` endpoint for
> Anthropic/Gemini — note Anthropic gates even `count_tokens` on a funded balance).
>
> The **Explorer** (`/api/projection/*`, `/api/project`) reduces vectors to 2-D
> with PCA, t-SNE (both from scikit-learn), and UMAP (`umap-learn`). UMAP is
> greyed out if `umap-learn` isn't installed; the "your dataset" source reuses
> the same local embedding model as Cosine similarity — no API key needed.

**2. Frontend** (http://localhost:5173):

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173, click **Load example** on the Datasets page, pick
some metrics, and run. (The frontend talks to `http://localhost:8000/api` by
default; override with `VITE_API_BASE` if needed.)

## Learn as you go

The app is built to teach, not just to score:

- **Metrics guide** (`/guide`, or the **📖 Metrics guide** toggle in the top bar):
  a reference page covering every metric — what it measures, how it's computed, a
  worked example, when to use it, and where it misleads — plus a **glossary** of
  the underlying concepts and links to the primary sources. Live availability
  ("needs install" / "needs API key") reflects the running backend.
- **`!` tips** sit next to every metric in the Run picker and every field in the
  Dataset editor. Hover for a one-line explanation; click to open the full entry
  in the guide in a new tab.
- **Explorer** (`/explore`, or **🔭 Explore** in the top bar): embed your dataset
  (or load a built-in demo like the 64-D digits) and project it to 2-D with
  **PCA, t-SNE, or UMAP** — compare them side-by-side and adjust their params
  (perplexity, n_neighbors, min_dist) to *see* how each algorithm behaves.

The teaching content lives in `frontend/src/content/metricGuide.ts` (the metric
prose + glossary), kept separate from the backend's `MetricInfo` so it can stay
long-form; the guide merges the two at render time.

> **Keep the guide fresh — review every 15 days.** The value of the guide
> depends on it staying accurate, so revisit `frontend/src/content/metricGuide.ts`
> on at least a **15-day cadence** and verify:
>
> - every external **link** / further-reading URL still resolves;
> - the metric prose still matches the scorers in `backend/app/metrics/`;
> - every registered metric has a guide entry, and any new concept has a
>   **glossary** term.
>
> Roll the next review forward 15 days each time, and note any content changes in
> the CHANGELOG.

## Test

```bash
cd backend && ./.venv/bin/python -m pytest      # metric math + API contract (fast; no model downloads)
cd frontend && npm run build                    # type-check (vue-tsc) + bundle
```

## Layout

```
backend/
  app/
    main.py            FastAPI app + CORS (loads backend/.env at startup)
    api.py             endpoints + scoring loop + confusion matrix + operational + estimate + projection
    models.py          Pydantic schemas (mirrored by frontend/src/api/types.ts)
    storage.py         SQLite-backed runs/datasets (LLM_EVAL_DB overridable)
    llm.py             provider-aware facade (routes by model id; availability, pricing, token/cost)
    providers/         one class per vendor — anthropic, openai, gemini + base/registry
    embeddings_util.py shared sentence-embedding helper (Cosine metric + Explorer)
    projection.py      DR engine: PCA/t-SNE/UMAP + built-in sample datasets
    metrics/           the metric engine: base, registry, and scorers — exact_match,
                       rouge, classification, embeddings, judge (LLM + RAG)
  tests/               pinned metric values + API contract + mocked-LLM + projection tests
  data/                SQLite db (gitignored, created on first run)
frontend/
  src/
    api/               typed client + types
    content/           metricGuide.ts — metric + DR explanations, glossary, links
    stores/            Pinia: dataset, run, metricsCatalog, providers, settings, projection
    views/             DatasetsView, RunView, ResultsView, GuideView, ExploreView, SettingsView
    components/        DatasetEditor, MetricPicker, ModelConfig, ModelSelect, RunControls,
                       EstimateCard, SummaryCards, ResultsTable, CaseInspector,
                       ConfusionMatrix, OperationalCard, MetricChart, RunComparison,
                       InfoTip, ScatterPlot
```
