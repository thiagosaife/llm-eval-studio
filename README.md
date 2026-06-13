# LLM Eval Studio

A browser-based tool that teaches developers how to evaluate Large Language
Model (LLM) outputs and computes the metrics for them. This repo implements
**Phases 1–2** of [the design doc](./docs/llm-eval-studio.md): the working
`dataset → score → display` loop, now extended with classification and
embedding metrics, import, and persistence.

- **Backend** — Python / FastAPI; lexical + classification + embedding metrics.
- **Frontend** — Vue 3 + TypeScript (Vite, Pinia, Vue Router).

## What works today (Phases 1–2)

- Build a dataset of test cases (input / prediction / reference / context);
  **import CSV** (with column → field mapping) or JSON; persisted in your browser.
- A metric picker that **explains each metric** ("read it" / "it lies when…"),
  greys out reference-based metrics until a gold answer exists, and greys out
  metrics whose libraries aren't installed.
- Metrics:
  - **Lexical** — Exact Match, ROUGE-1 / ROUGE-2 / ROUGE-L (pure Python).
  - **Classification** — Accuracy, Precision, Recall, F1 (macro) + a **confusion
    matrix**. Precision/Recall/F1 are set-level (summary cards only).
  - **Semantic** — Cosine similarity (sentence-transformers) and BERTScore.
- A results dashboard: aggregate summary cards, a per-case table sortable by
  any metric (defaults to worst-first), a confusion matrix for label tasks, and
  a case inspector with a **word-level diff**.
- Runs are persisted in **SQLite**, so a `/results/:id` link survives a restart.

The metric engine is a registry (`backend/app/metrics/`): adding a metric is
"write one class, register it," and it appears in the UI automatically. Each
metric exposes a `score()` (per-case) and an `aggregate()` hook (set-level
metrics like precision override it). That's the seam Phase 3 (LLM-as-a-judge,
RAG triad, operational metrics, run-vs-run charts) plugs into.

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
    api.py             endpoints + the scoring loop + confusion matrix
    models.py          Pydantic schemas (mirrored by frontend/src/api/types.ts)
    storage.py         SQLite-backed runs/datasets
    metrics/           the metric engine: base, registry, and scorers —
                       exact_match, rouge, classification, embeddings
  tests/               pinned metric values + API contract tests
  data/                SQLite db (gitignored, created on first run)
frontend/
  src/
    api/               typed client + types
    stores/            Pinia: dataset, run, metricsCatalog
    views/             DatasetsView, RunView, ResultsView
    components/        DatasetEditor, MetricPicker, RunControls, SummaryCards,
                       ResultsTable, CaseInspector, ConfusionMatrix
```
