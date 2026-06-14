"""FastAPI application entry point.

Run with:  uvicorn app.main:app --reload --port 8000
Interactive API docs (a learning aid, doc §5.1) live at /docs.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load backend/.env (e.g. ANTHROPIC_API_KEY) into the environment before anything
# reads it, so `uvicorn app.main:app` just works without `--env-file`. Path is
# resolved relative to this file so the cwd doesn't matter; existing env vars win
# (load_dotenv does not override them). No-op if python-dotenv isn't installed.
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

from .api import router  # noqa: E402  (imported after .env is loaded above)

app = FastAPI(
    title="LLM Eval Studio API",
    version="0.1.0",
    description="Score LLM outputs with lexical, semantic, and judge-based metrics.",
)

# The Vite dev server runs on :5173. Allow it (and the 127.0.0.1 alias) so the
# browser app can call the API during local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
