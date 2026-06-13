"""SQLite-backed storage (doc §7: "store runs in SQLite — zero setup").

Runs and datasets are kept as JSON blobs of their Pydantic models — the schema
*is* the model, so there are no migrations to babysit while the shape is still
moving. This is the Phase 2 upgrade over Phase 1's in-memory dicts: runs now
survive a server restart, so a `/results/:id` link keeps working.

A connection is opened per call. FastAPI runs sync endpoints in a threadpool, so
per-call connections sidestep SQLite's single-thread rule without a global lock.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from .models import Dataset, RunResponse

_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "eval.db"


def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS datasets (id TEXT PRIMARY KEY, data TEXT NOT NULL)")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS runs "
        "(id TEXT PRIMARY KEY, created_at TEXT NOT NULL, data TEXT NOT NULL)"
    )
    return conn


def save_dataset(dataset: Dataset) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO datasets (id, data) VALUES (?, ?)",
            (dataset.id, dataset.model_dump_json()),
        )


def get_dataset(dataset_id: str) -> Optional[Dataset]:
    with _connect() as conn:
        row = conn.execute("SELECT data FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
    return Dataset.model_validate_json(row[0]) if row else None


def save_run(run: RunResponse) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO runs (id, created_at, data) VALUES (?, ?, ?)",
            (run.run_id, run.created_at, run.model_dump_json()),
        )


def get_run(run_id: str) -> Optional[RunResponse]:
    with _connect() as conn:
        row = conn.execute("SELECT data FROM runs WHERE id = ?", (run_id,)).fetchone()
    return RunResponse.model_validate_json(row[0]) if row else None
