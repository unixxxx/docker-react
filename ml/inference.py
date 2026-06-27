"""Model loading + inference, with a graceful no-model fallback.

The backend calls ``predict(ctx)``. If a trained artifact exists it returns an
ML probability + confidence; if not, it returns ``None`` and the decision
engine falls back to the rule score. The artifact is cached in-process and
hot-reloaded when the file changes (so nightly retraining is picked up without
a restart).
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass

import joblib

from core.features import SessionContext, build_features, feature_vector
from ml.train import DEFAULT_MODEL_PATH

_lock = threading.Lock()
_cache: dict = {"path": None, "mtime": None, "artifact": None}


@dataclass
class Prediction:
    probability: float       # 0..1 probability of success
    confidence: float        # 0..1, derived from distance from 0.5
    model_kind: str
    trained_at: str
    n_samples: int


def _load_artifact(model_path: str):
    """Load (and cache) the model artifact, reloading if the file changed."""
    if not os.path.exists(model_path):
        return None
    mtime = os.path.getmtime(model_path)
    with _lock:
        if _cache["path"] == model_path and _cache["mtime"] == mtime:
            return _cache["artifact"]
        artifact = joblib.load(model_path)
        _cache.update({"path": model_path, "mtime": mtime, "artifact": artifact})
        return artifact


def model_available(model_path: str = DEFAULT_MODEL_PATH) -> bool:
    return os.path.exists(model_path)


def model_info(model_path: str = DEFAULT_MODEL_PATH) -> dict | None:
    artifact = _load_artifact(model_path)
    if artifact is None:
        return None
    return {
        "model_kind": artifact.get("model_kind"),
        "trained_at": artifact.get("trained_at"),
        "n_samples": artifact.get("n_samples"),
        "metrics": artifact.get("metrics"),
    }


def predict(ctx: SessionContext, model_path: str = DEFAULT_MODEL_PATH) -> Prediction | None:
    """Return a ``Prediction`` or ``None`` if no model is trained yet."""
    artifact = _load_artifact(model_path)
    if artifact is None:
        return None

    model = artifact["model"]
    feats = build_features(ctx)
    vec = [feature_vector(feats)]

    proba = float(model.predict_proba(vec)[0][1])
    # Confidence: how far the probability sits from a coin flip, scaled to 0..1.
    confidence = min(1.0, abs(proba - 0.5) * 2.0)

    return Prediction(
        probability=proba,
        confidence=confidence,
        model_kind=artifact.get("model_kind", "unknown"),
        trained_at=artifact.get("trained_at", ""),
        n_samples=int(artifact.get("n_samples", 0)),
    )
