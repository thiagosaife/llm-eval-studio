"""FastAPI application entry point.

Run with:  uvicorn app.main:app --reload --port 8000
Interactive API docs (a learning aid, doc §5.1) live at /docs.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router

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
