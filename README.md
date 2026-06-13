# LLM Eval Studio

A browser-based tool that teaches developers how to evaluate Large Language
Model (LLM) outputs and computes the metrics for them. This repo implements
**all three phases** of [the design doc](./docs/llm-eval-studio.md): the working
`dataset → score → display` loop, extended with classification + embedding
metrics, import/persistence, and live generation + LLM-as-a-judge + RAG +
operational metrics + run comparison.

- **Backend** — Python / FastAPI; lexical, classification, embedding, and
  Claude-based (judge / RAG / generation) metrics.
- **Frontend** — Vue 3 + TypeScript (Vite, Pinia, Vue Router).

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
> **For live generation + LLM-judge + RAG metrics**, set `ANTHROPIC_API_KEY` in
> the backend environment (e.g. `export ANTHROPIC_API_KEY=sk-ant-...` before
> `uvicorn`). Without it, those features are greyed out and everything else still
> works. The default model is `claude-opus-4-8`.

**2. Frontend** (http://localhost:5173):

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173, click **Load example** on the Datasets page, pick
some metrics, and run. (The frontend talks to `http://localhost:8000/api` by
default; override with `VITE_API_BASE` if needed.)

## Test

```bash
cd backend && ./.venv/bin/python -m pytest      # metric math + API contract (fast; no model downloads)
cd frontend && npm run build                    # type-check (vue-tsc) + bundle
```

## Layout

```
backend/
  app/
    main.py            FastAPI app + CORS
    api.py             endpoints + scoring loop + confusion matrix + operational
    models.py          Pydantic schemas (mirrored by frontend/src/api/types.ts)
    storage.py         SQLite-backed runs/datasets (LLM_EVAL_DB overridable)
    llm.py             the one place that calls Claude (availability, pricing)
    metrics/           the metric engine: base, registry, and scorers — exact_match,
                       rouge, classification, embeddings, judge (LLM + RAG)
  tests/               pinned metric values + API contract + mocked-LLM tests
  data/                SQLite db (gitignored, created on first run)
frontend/
  src/
    api/               typed client + types
    stores/            Pinia: dataset, run, metricsCatalog
    views/             DatasetsView, RunView, ResultsView
    components/        DatasetEditor, MetricPicker, ModelConfig, RunControls,
                       SummaryCards, ResultsTable, CaseInspector, ConfusionMatrix,
                       OperationalCard, MetricChart, RunComparison
```
