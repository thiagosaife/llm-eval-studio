"""The dimensionality-reduction engine behind the Explorer (the /api/project* endpoints).

Takes high-dimensional vectors — sentence embeddings of the user's eval cases, or
a built-in teaching dataset — and projects them to 2-D with PCA, t-SNE, or UMAP so
they can be plotted. The point is pedagogical: swap the algorithm (and its params)
and *see* how each one lays the same data out.

Design notes:
- PCA and t-SNE come from scikit-learn (always installed). UMAP is optional
  (`umap-learn`); `algorithm_infos()` reports availability so the UI greys it out
  rather than letting a request fail — same pattern as the metric registry.
- Heavy libs (sklearn estimators, umap) are imported lazily inside `reduce()`, so
  importing this module is cheap and the server boots instantly.
- A fixed `random_state` makes t-SNE/UMAP reproducible: the same input always
  yields the same picture, which matters when you're teaching.
- For high-dimensional input (e.g. 384-D embeddings) we PCA-preprocess to ~50
  dims before t-SNE/UMAP — standard practice that speeds them up and denoises —
  and record that in the result meta.
"""
from __future__ import annotations

import importlib.util
from typing import Dict, List, Optional, Tuple

import numpy as np

_RANDOM_STATE = 42
_PREPROCESS_DIMS = 50  # PCA target before t-SNE/UMAP on high-D input


# --- availability -----------------------------------------------------------

def _has(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def _sklearn_ok() -> bool:
    return _has("sklearn")


# --- algorithm catalog ------------------------------------------------------
# Each param spec drives a labelled slider in the UI: key, label, kind, default,
# min, max, step, and a one-line help string (also shown in the guide).

_ALGORITHMS: List[dict] = [
    {
        "id": "pca",
        "name": "PCA",
        "description": (
            "Principal Component Analysis — a fast, deterministic linear projection "
            "onto the two directions of greatest variance. Distances and global "
            "structure are meaningful; subtle nonlinear clusters can be hidden."
        ),
        "params": [],
        "module": None,  # sklearn only
    },
    {
        "id": "tsne",
        "name": "t-SNE",
        "description": (
            "t-distributed Stochastic Neighbor Embedding — a nonlinear method that "
            "preserves local neighborhoods, so similar points form tight clusters. "
            "Cluster sizes and the distances between clusters are NOT meaningful."
        ),
        "params": [
            {
                "key": "perplexity",
                "label": "Perplexity",
                "kind": "int",
                "default": 30,
                "min": 2,
                "max": 50,
                "step": 1,
                "help": "Roughly how many neighbors each point balances. Lower = more, tighter local clusters; must stay below the number of points.",
            }
        ],
        "module": None,
    },
    {
        "id": "umap",
        "name": "UMAP",
        "description": (
            "Uniform Manifold Approximation and Projection — a nonlinear method that "
            "balances local and global structure better than t-SNE and runs faster. "
            "Tune n_neighbors (local vs global) and min_dist (how tightly points pack)."
        ),
        "params": [
            {
                "key": "n_neighbors",
                "label": "n_neighbors",
                "kind": "int",
                "default": 15,
                "min": 2,
                "max": 100,
                "step": 1,
                "help": "Size of the local neighborhood. Low = fine local detail; high = more global structure.",
            },
            {
                "key": "min_dist",
                "label": "min_dist",
                "kind": "float",
                "default": 0.1,
                "min": 0.0,
                "max": 0.99,
                "step": 0.05,
                "help": "Minimum spacing between points in 2-D. Low = tight clumps; high = more even spread.",
            },
        ],
        "module": "umap",
    },
]

_ALGO_BY_ID = {a["id"]: a for a in _ALGORITHMS}


def _algo_available(algo: dict) -> Tuple[bool, Optional[str]]:
    if not _sklearn_ok():
        return False, "Needs scikit-learn — `pip install scikit-learn`."
    if algo["module"] and not _has(algo["module"]):
        return False, f"Needs {algo['module']} — `pip install umap-learn`."
    return True, None


def algorithm_infos() -> List[dict]:
    """Catalog for GET /api/projection/algorithms (drives the picker + gating)."""
    out: List[dict] = []
    for algo in _ALGORITHMS:
        ok, reason = _algo_available(algo)
        out.append(
            {
                "id": algo["id"],
                "name": algo["name"],
                "description": algo["description"],
                "params": algo["params"],
                "available": ok,
                "unavailable_reason": reason,
            }
        )
    return out


def is_available(algorithm_id: str) -> bool:
    algo = _ALGO_BY_ID.get(algorithm_id)
    return bool(algo) and _algo_available(algo)[0]


# --- built-in teaching datasets ---------------------------------------------

_SAMPLES: List[dict] = [
    {
        "id": "digits",
        "name": "Handwritten digits",
        "description": "8×8 grayscale images of digits 0–9 as 64-D vectors. Ten clear clusters — a classic DR demo.",
        "n_features": 64,
        "full": 1797,
        "cap": 500,
    },
    {
        "id": "iris",
        "name": "Iris flowers",
        "description": "150 iris flowers in 4 dimensions (petal/sepal measurements), labelled by species. Tiny and instant.",
        "n_features": 4,
        "full": 150,
        "cap": None,
    },
]

_SAMPLE_BY_ID = {s["id"]: s for s in _SAMPLES}


def _sample_count(spec: dict) -> int:
    return min(spec["cap"], spec["full"]) if spec["cap"] is not None else spec["full"]


def sample_infos() -> List[dict]:
    """Catalog for GET /api/projection/samples."""
    return [
        {
            "id": s["id"],
            "name": s["name"],
            "description": s["description"],
            "n_samples": _sample_count(s),
            "n_features": s["n_features"],
        }
        for s in _SAMPLES
    ]


def load_sample(sample_id: str) -> Tuple[np.ndarray, List[str], dict]:
    """Return (vectors, labels, info) for a built-in dataset, subsampled if capped."""
    spec = _SAMPLE_BY_ID.get(sample_id)
    if spec is None:
        raise KeyError(sample_id)

    if sample_id == "digits":
        from sklearn.datasets import load_digits

        data = load_digits()
        X, y = data.data, data.target
        labels = [str(int(v)) for v in y]
    elif sample_id == "iris":
        from sklearn.datasets import load_iris

        data = load_iris()
        X = data.data
        labels = [data.target_names[int(v)] for v in data.target]
    else:  # pragma: no cover - guarded by the registry
        raise KeyError(sample_id)

    cap = spec["cap"]
    if cap is not None and X.shape[0] > cap:
        rng = np.random.default_rng(_RANDOM_STATE)
        idx = rng.choice(X.shape[0], size=cap, replace=False)
        X = X[idx]
        labels = [labels[i] for i in idx]

    return np.asarray(X, dtype=float), labels, spec


# --- the reduction itself ---------------------------------------------------

def _clamp(value, lo, hi):
    return max(lo, min(hi, value))


def _maybe_pca_preprocess(vectors: np.ndarray) -> Tuple[np.ndarray, Optional[int]]:
    """PCA-shrink high-D input before t-SNE/UMAP (speed + denoise)."""
    n_samples, n_features = vectors.shape
    target = min(_PREPROCESS_DIMS, n_features, n_samples)
    if n_features <= _PREPROCESS_DIMS:
        return vectors, None
    from sklearn.decomposition import PCA

    reduced = PCA(n_components=target, random_state=_RANDOM_STATE).fit_transform(vectors)
    return reduced, target


def reduce(
    vectors: np.ndarray, algorithm: str, params: Optional[Dict] = None
) -> Tuple[np.ndarray, dict]:
    """Project (n, d) vectors to (n, 2). Returns (coords, meta).

    meta carries the teaching signals: PCA variance explained, the actual
    perplexity / n_neighbors used (after clamping to the data size), and whether
    we PCA-preprocessed.
    """
    params = params or {}
    n_samples = vectors.shape[0]
    meta: dict = {}

    if algorithm == "pca":
        from sklearn.decomposition import PCA

        # Exact SVD: deterministic and warning-free (the result a learner sees
        # for the same data never changes).
        model = PCA(n_components=2, svd_solver="full", random_state=_RANDOM_STATE)
        coords = model.fit_transform(vectors)
        meta["variance_explained"] = [round(float(v), 4) for v in model.explained_variance_ratio_[:2]]
        return coords, meta

    if algorithm == "tsne":
        from sklearn.manifold import TSNE

        pre, pre_dims = _maybe_pca_preprocess(vectors)
        if pre_dims:
            meta["preprocessed_dims"] = pre_dims
        # sklearn requires perplexity < n_samples.
        requested = int(params.get("perplexity", 30))
        perplexity = _clamp(requested, 2, max(2, n_samples - 1))
        meta["perplexity"] = perplexity
        model = TSNE(
            n_components=2,
            perplexity=perplexity,
            init="pca",
            learning_rate="auto",
            random_state=_RANDOM_STATE,
        )
        return model.fit_transform(pre), meta

    if algorithm == "umap":
        import umap  # type: ignore

        pre, pre_dims = _maybe_pca_preprocess(vectors)
        if pre_dims:
            meta["preprocessed_dims"] = pre_dims
        n_neighbors = _clamp(int(params.get("n_neighbors", 15)), 2, max(2, n_samples - 1))
        min_dist = _clamp(float(params.get("min_dist", 0.1)), 0.0, 0.99)
        meta["n_neighbors"] = n_neighbors
        meta["min_dist"] = round(min_dist, 3)
        model = umap.UMAP(
            n_components=2,
            n_neighbors=n_neighbors,
            min_dist=min_dist,
            random_state=_RANDOM_STATE,
        )
        return model.fit_transform(pre), meta

    raise ValueError(f"Unknown algorithm '{algorithm}'")
