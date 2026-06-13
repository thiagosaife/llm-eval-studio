# LLM Eval Studio — Design Document

*A browser-based tool that teaches developers how to evaluate Large Language Model (LLM) outputs and computes the metrics for them.*

**Stack:** Vue 3 + TypeScript (frontend) · Python / FastAPI (backend)
**Audience for this doc:** an engineer who is strong at frontend/systems work but new to LLM evaluation.

---

## 1. What this tool is (and why it exists)

When you write normal software, you can check it with a unit test: "given input X, the function should return exactly Y." LLMs break this assumption. The same prompt can produce different wording every time, and two completely different sentences can both be *correct*. So "is this output good?" is no longer a yes/no equality check — it's a measurement problem.

**LLM Eval Studio** is a web app where a developer can:

1. Bring a set of test cases (a prompt, and optionally an "ideal" answer).
2. Feed in the LLM's actual outputs (pasted, uploaded, or generated live).
3. Pick which evaluation metrics to run.
4. Get back per-case scores, aggregate numbers, and visualizations — with inline explanations of what each metric means and how to read it.

The "studio" part matters: the goal isn't just to dump numbers, it's to **guide** the user. Each metric in the UI has a short "what this tells you / when it lies to you" note, so someone learning the field builds the right intuitions.

> **Mental model:** think of it as a "test runner" for LLM outputs. A dataset is your test suite, a *run* is one execution, and metrics are your assertions — except the assertions return a score from 0 to 1 instead of pass/fail.

---

## 2. The concepts you need before the metrics make sense

This section is the conceptual foundation. The metrics in Section 3 are just concrete implementations of these ideas.

### 2.1 Reference-based vs. reference-free evaluation

There are two fundamentally different situations:

- **Reference-based** — you have a "gold" / "expected" answer to compare against. The metric measures how close the LLM's output is to that reference. (Like comparing a student's answer to the answer key.)
- **Reference-free** — you have no gold answer (this is common in real generative tasks). Instead you measure intrinsic qualities: Is it fluent? Is it relevant to the question? Does it contradict the source document? Often another LLM does the judging here.

A lot of beginner confusion comes from applying a reference-based metric where you have no good reference. Knowing which situation you're in tells you which metrics are even valid.

### 2.2 Three families of "how" you measure

| Family | How it works | Strengths | Weaknesses |
|---|---|---|---|
| **Lexical / overlap** (BLEU, ROUGE, Exact Match) | Counts overlapping words/word-sequences between output and reference | Fast, cheap, deterministic | Blind to meaning — punishes valid paraphrases |
| **Semantic / embedding** (BERTScore, cosine similarity) | Converts text to vectors and compares *meaning* | Rewards correct paraphrases | Slower, needs a model, can over-reward fluent nonsense |
| **Model-as-judge** (LLM-as-a-judge) | A strong LLM grades the output against a rubric | Flexible, handles open-ended tasks, closest to human judgment | Costs money/time, has its own biases, non-deterministic |

A mature eval setup usually combines all three rather than trusting any single number.

### 2.3 The evaluation lifecycle

Every run, regardless of metric, follows the same loop. This is the backbone the whole app is built around:

```
Dataset  →  Generate (or import) outputs  →  Score with metrics  →  Aggregate & inspect  →  Iterate
```

1. **Dataset** — a collection of test cases.
2. **Generate / import** — either the tool calls the LLM live, or you paste outputs you already produced.
3. **Score** — run the selected metrics over each case.
4. **Aggregate & inspect** — see the averages, then drill into individual cases (the average hides the failures).
5. **Iterate** — tweak the prompt/model, re-run, and compare runs to see if you improved.

---

## 3. The metrics, explained

This is the heart of the "guide the developer" goal. Below, each metric has: *what it measures*, *its range and how to read it*, and *how it can mislead you*. In the UI, a condensed version of these notes appears next to each result.

### 3.1 Lexical / overlap metrics (reference-based)

**Exact Match (EM)**
Returns 1 if the output equals the reference (after light normalization like lowercasing and trimming), else 0. Perfect for closed questions with a single right answer ("What's the capital of France?"). Useless for anything free-form, because one extra word makes it fail.

**BLEU**
Originally built for machine translation. It measures **precision of overlapping n-grams** (sequences of 1–4 words) and applies a "brevity penalty" so the model can't cheat by outputting one correct word. Range 0–1 (often shown ×100). Higher = more shared word-sequences with the reference. *It lies when* the output is a perfectly good paraphrase that happens to use different words — BLEU scores it low even though a human would call it correct.

**ROUGE (ROUGE-1, ROUGE-2, ROUGE-L)**
The summarization counterpart to BLEU, and **recall-oriented** — it asks "how much of the reference did the output capture?" ROUGE-1 looks at single words, ROUGE-2 at word pairs, ROUGE-L at the longest common subsequence. Range 0–1. *It lies* the same way BLEU does (synonyms hurt it), and high recall doesn't mean the summary is concise or non-redundant.

**METEOR**
An upgrade on BLEU that also credits synonyms and word stems (so "running" ≈ "ran"), which makes it correlate better with human judgment. Still fundamentally a word-matching metric.

### 3.2 Semantic / embedding metrics (reference-based, meaning-aware)

**BERTScore**
Instead of matching exact words, it converts both texts into contextual embeddings and matches tokens by similarity, then reports precision/recall/F1. The big win: a correct paraphrase scores high even with zero word overlap. *It lies* when text is fluent and on-topic but factually wrong — semantic closeness isn't the same as correctness.

**Cosine similarity of sentence embeddings**
The simplest semantic metric: encode the output and the reference each into one vector (via a sentence-transformer model) and measure the cosine of the angle between them. Range roughly 0–1. Great for a quick "are these two answers about the same thing?" signal; coarser than BERTScore.

### 3.3 Classification metrics (when the output is a label)

If your LLM task is really classification (sentiment, intent, yes/no, category), treat it like one and use the standard ML metrics:

- **Accuracy** — fraction of cases the model got right. Misleading on imbalanced data (95% accuracy is bad if 95% of cases are one class).
- **Precision** — of the cases the model called positive, how many actually were. (Penalizes false alarms.)
- **Recall** — of the truly positive cases, how many the model caught. (Penalizes misses.)
- **F1** — the harmonic mean of precision and recall; the single number to watch when you care about both.
- **Confusion matrix** — the full breakdown of right/wrong per class; this is what you actually look at to debug.

### 3.4 Model-based / reference-free metrics

**Perplexity**
Measures how "surprised" a language model is by a piece of text — lower means more fluent and predictable. It tells you about *fluency*, never about *correctness or truth*. Useful as a sanity signal, dangerous as a quality score on its own.

**LLM-as-a-judge**
You give a strong model a rubric ("Rate this answer's correctness 1–5, and explain why") and let it grade. This is the most practical approach for open-ended generation because it handles nuance no overlap metric can. Be aware of its **known biases**: it tends to prefer longer answers (verbosity bias), favor whichever answer it sees first (position bias), and rate its own outputs higher (self-preference). Mitigations: randomize order, force a structured rubric, and spot-check against human labels.

### 3.5 RAG-specific metrics (the "triad")

If the system retrieves documents and then answers from them (Retrieval-Augmented Generation), three questions matter, and there are metrics (typically LLM-judged) for each:

- **Faithfulness / groundedness** — does the answer stick to the retrieved context, or did it hallucinate?
- **Answer relevancy** — does the answer actually address the question asked?
- **Context relevancy / precision / recall** — did the retriever fetch the *right* documents in the first place?

Separating these lets you tell whether a bad answer is a *retrieval* problem or a *generation* problem — a distinction that's invisible if you only score the final text.

### 3.6 Operational metrics (always worth tracking)

These aren't about quality but about whether the system is shippable:

- **Latency** (median and p95 — the tail matters for UX)
- **Tokens** in/out per call
- **Cost** per call and per run
- **Throughput** (requests/sec)

A model that's 2% better but 5× slower and 10× more expensive is often the wrong choice; showing these next to quality metrics keeps that trade-off honest.

### 3.7 Quick "which metric do I reach for?" guide

| Your task | Start with |
|---|---|
| Single correct answer (factual QA) | Exact Match, then LLM-judge for partial credit |
| Translation | BLEU, METEOR |
| Summarization | ROUGE, plus BERTScore |
| Paraphrase / open generation | BERTScore + LLM-as-a-judge |
| Classification / labeling | Accuracy, Precision, Recall, F1, confusion matrix |
| RAG / chatbot over docs | Faithfulness + Answer relevancy + Context relevancy |
| Any production system | Add latency / tokens / cost |

---

## 4. System architecture

The app is a classic two-tier web app. The browser handles all interaction and visualization; Python does the heavy lifting (running metric libraries and ML models, which mostly live in the Python ecosystem — this is the main reason the backend is Python).

```
┌─────────────────────────────────────────────┐
│                  Browser                      │
│   Vue 3 + TypeScript (Vite, Pinia, Router)    │
│  ┌─────────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Dataset UI  │  │ Eval     │  │ Results  │  │
│  │ (upload/    │  │ config & │  │ dashboard│  │
│  │  edit cases)│  │ run      │  │ + charts │  │
│  └─────────────┘  └──────────┘  └──────────┘  │
└───────────────────────┬───────────────────────┘
                         │  HTTP / JSON (REST)
                         ▼
┌─────────────────────────────────────────────┐
│            Python backend (FastAPI)           │
│  ┌──────────────┐   ┌────────────────────┐    │
│  │  API layer   │   │   Metric engine     │   │
│  │ (endpoints,  │──▶│ lexical / semantic /│   │
│  │  validation) │   │ classification /    │   │
│  └──────────────┘   │ judge / RAG         │   │
│         │           └────────────────────┘    │
│         ▼                                      │
│  ┌──────────────┐   ┌────────────────────┐    │
│  │ LLM clients  │   │  Storage           │    │
│  │ (optional    │   │ (SQLite / files)   │    │
│  │  live gen)   │   └────────────────────┘    │
│  └──────────────┘                              │
└─────────────────────────────────────────────┘
```

**Why this split:** the mature, battle-tested implementations of BLEU, ROUGE, BERTScore, embeddings, and RAG evaluation are Python libraries. Re-implementing them in TypeScript would be error-prone and is exactly the kind of thing you don't want to get subtly wrong in an eval tool. So Python owns *measurement*, and Vue owns *experience*.

---

## 5. Backend design (Python / FastAPI)

### 5.1 Why FastAPI

FastAPI gives you async endpoints (useful when calling slow LLM APIs), automatic request/response validation via Pydantic, and auto-generated interactive API docs at `/docs` — which is itself a learning aid while you build.

### 5.2 Core libraries

| Purpose | Library |
|---|---|
| Web framework / validation | `fastapi`, `pydantic`, `uvicorn` |
| Unified metric API (BLEU/ROUGE/etc.) | `evaluate` (Hugging Face) |
| BLEU (standardized) | `sacrebleu` |
| ROUGE | `rouge-score` |
| BERTScore | `bert-score` |
| Tokenization / METEOR | `nltk` |
| Embeddings (cosine similarity) | `sentence-transformers` |
| Classification metrics | `scikit-learn` |
| LLM-judge & RAG metrics (higher level) | `ragas` and/or `deepeval` |
| Live generation / judging calls | provider SDK (e.g. `anthropic`, `openai`) or `litellm` for a unified interface |

Start with the lexical and classification metrics — they're pure-Python, fast, and have no model downloads. Add the embedding/judge metrics once the pipeline works, since they pull in larger dependencies.

### 5.3 API endpoints (suggested)

| Method & path | Purpose |
|---|---|
| `GET /api/metrics` | List available metrics, each with `id`, `name`, `description`, `requires_reference`, `range`. Drives the UI's metric picker and the inline explanations. |
| `POST /api/datasets` | Create/import a dataset of test cases (also accepts CSV/JSON upload). |
| `GET /api/datasets/{id}` | Fetch a dataset. |
| `POST /api/evaluate` | The main call. Takes cases + selected metric IDs (+ optional model config for live generation), returns per-case and aggregate scores. |
| `POST /api/generate` | Optional: call an LLM live to produce outputs for the dataset. |
| `GET /api/runs/{id}` | Retrieve a stored run for the dashboard / comparisons. |

### 5.4 The metric engine pattern

Keep each metric behind a common interface so the API doesn't care which family it belongs to. A simple, extensible shape:

```python
# metrics/base.py
from typing import Protocol

class Metric(Protocol):
    id: str
    requires_reference: bool

    def score(self, prediction: str, reference: str | None,
              context: str | None = None) -> float:
        ...
```

Then each concrete metric (a ROUGE scorer, a BERTScore scorer, an LLM-judge scorer) implements `score`, and a registry maps `id → metric`. Adding a new metric becomes "write one class, register it" — and it automatically appears in the UI because `GET /api/metrics` reads the registry. This is the single most important design decision for keeping the project maintainable.

### 5.5 Request / response shape (example)

```jsonc
// POST /api/evaluate  — request
{
  "metrics": ["rouge", "bertscore", "llm_judge"],
  "cases": [
    {
      "id": "case-1",
      "input": "Summarize the paragraph below.",
      "prediction": "The company grew revenue 12% last quarter.",
      "reference": "Revenue rose 12% quarter over quarter.",
      "context": null
    }
  ]
}

// response
{
  "run_id": "run-abc123",
  "per_case": [
    {
      "id": "case-1",
      "scores": { "rouge": 0.71, "bertscore": 0.93, "llm_judge": 0.80 }
    }
  ],
  "aggregate": { "rouge": 0.71, "bertscore": 0.93, "llm_judge": 0.80 }
}
```

---

## 6. Frontend design (Vue 3 + TypeScript)

Build with Vite, manage shared state with Pinia, and use Vue Router for the three main views. A typed API client wraps `fetch`/`axios` so every response is checked against an interface that mirrors the backend's Pydantic models — keep those two definitions in sync and the whole app stays type-safe end to end.

### 6.1 Views (routes)

- **`/datasets`** — create, edit, and upload test cases.
- **`/run`** — pick a dataset, select metrics, optionally configure a model, and launch.
- **`/results/:runId`** — the dashboard (aggregate cards, per-case table, charts, side-by-side inspector).

### 6.2 Key components

| Component | Responsibility |
|---|---|
| `DatasetEditor` | Add/edit cases; import CSV/JSON; mark which column is input / reference / context. |
| `MetricPicker` | Lists metrics from `GET /api/metrics`. Each shows its description and a "requires reference" badge, and disables metrics you can't run (e.g. greys out reference-based metrics when no reference exists). **This is where most of the "teaching" happens.** |
| `RunControls` | Choose live-generation vs. import; trigger `POST /api/evaluate`; show progress. |
| `SummaryCards` | One card per metric with the aggregate score, its 0–1 range, and a one-line "how to read this." |
| `ResultsTable` | Per-case rows; sortable by any metric so the user can jump straight to the worst cases. |
| `CaseInspector` | Side-by-side prediction vs. reference with a word-diff, plus all metric scores and (for LLM-judge) the judge's written rationale. |
| `MetricChart` | Distribution / comparison charts (e.g. a histogram of scores, or run-vs-run bars). Use a charting lib such as Chart.js or ECharts via a Vue wrapper. |

### 6.3 State (Pinia stores)

- `datasetStore` — current dataset and cases.
- `runStore` — selected metrics, run status, and results.
- `metricsCatalogStore` — the metric definitions fetched once from the backend (so descriptions/ranges are always consistent with the engine).

### 6.4 A UX principle worth holding to

Always show the **per-case drill-down**, not just averages. The single most common eval mistake is celebrating a high average while a cluster of cases is failing badly. Sorting the table by the worst score and reading those specific outputs is where the real insight comes from — design the UI to make that the easy, obvious next click.

---

## 7. Data model

```
Dataset
 ├─ id
 ├─ name
 └─ cases: TestCase[]

TestCase
 ├─ id
 ├─ input        (the prompt / question)
 ├─ reference?   (gold answer — optional; enables reference-based metrics)
 ├─ context?     (retrieved docs — optional; enables RAG metrics)
 └─ prediction?  (the LLM output — pasted, imported, or generated)

Run
 ├─ id
 ├─ dataset_id
 ├─ model_config?   (which model + params, if generated live)
 ├─ metrics[]       (which metrics were applied)
 ├─ created_at
 └─ results: CaseResult[]

CaseResult
 ├─ case_id
 ├─ prediction
 ├─ scores: { [metricId]: number }
 ├─ judge_rationale?   (text, when LLM-judge was used)
 └─ operational?       (latency_ms, tokens_in, tokens_out, cost)
```

For an MVP, store runs in **SQLite** (zero setup) or even flat JSON files. Reach for Postgres only if/when you need multi-user history.

---

## 8. End-to-end user workflow

1. **Build a dataset** — paste or upload 10–50 cases. (Small is fine; a tiny, well-chosen set beats a huge noisy one when you're learning.) Mark which fields are input, reference, and context.
2. **Pick metrics** — the picker only offers metrics that fit your data and explains each one.
3. **Provide outputs** — either paste outputs you already have, or let the tool generate them live from a configured model.
4. **Run** — the backend scores every case and returns aggregates + per-case results.
5. **Read the dashboard** — glance at the summary cards, then *sort by the worst metric* and open failing cases in the inspector to understand *why* they failed.
6. **Iterate** — change the prompt or model, run again, and compare the two runs side by side to confirm you actually improved.

---

## 9. Suggested build order (so you're never stuck on dependencies)

**Phase 1 — Skeleton (prove the loop):**
Vue app with the three routes + a typed API client; FastAPI with `GET /api/metrics` and a `POST /api/evaluate` that supports **Exact Match** and **ROUGE** only (pure Python, instant). Outputs are pasted, results held in memory. This gets the full dataset → score → display loop working with the lightest possible dependencies.

**Phase 2 — Make it useful:**
Add classification metrics (`scikit-learn`), embedding metrics (BERTScore + cosine via `sentence-transformers`), CSV/JSON import, the case inspector with word-diff, and SQLite persistence so runs survive a refresh.

**Phase 3 — Make it impressive:**
Live generation through a provider SDK, **LLM-as-a-judge** with a configurable rubric and rationale display, RAG metrics via `ragas`/`deepeval`, operational metrics (latency/tokens/cost), and run-to-run comparison charts.

Building in this order means each phase ships something demonstrable, and the heavy ML dependencies only arrive once the architecture is proven.

---

## 10. Glossary

- **Token** — the chunk of text an LLM actually processes (roughly ¾ of a word on average). Cost and length are measured in tokens.
- **Reference / gold answer** — the known-correct answer you compare against.
- **n-gram** — a sequence of *n* consecutive words; the unit lexical metrics count.
- **Embedding** — a numeric vector representing a piece of text's meaning; similar meanings sit close together in vector space.
- **Hallucination** — when a model states something unsupported by its input or by fact.
- **RAG (Retrieval-Augmented Generation)** — a system that retrieves documents and then answers using them.
- **LLM-as-a-judge** — using a strong LLM, guided by a rubric, to grade another model's output.
- **p95 latency** — the response time that 95% of requests come in under; a measure of worst-case-ish speed.

---

*This document describes the design only. Phase 1 in Section 9 is the recommended starting point for implementation.*
