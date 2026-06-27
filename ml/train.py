"""Training pipeline.

Steps (as specified):
  1. extract features from sessions
  2. build dataset
  3. train model
  4. evaluate accuracy
  5. save model artifact

We default to scikit-learn's ``GradientBoostingClassifier`` (a strong,
always-available stand-in for XGBoost) and fall back to ``LogisticRegression``
on very small datasets. If ``xgboost`` is installed and ``--model xgboost`` is
passed, it is used instead.

Run nightly (the data flywheel) or on demand:

    python -m ml.train                  # train from the backend DB
    python -m ml.train --synthetic 500  # train on generated data (cold start)
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone

import joblib
import numpy as np

from core.features import FEATURE_NAMES, SessionContext, WeatherSnapshot
from ml.dataset import build_dataset, build_dataset_from_db

# Where the trained artifact lives. Override with FISHING_MODEL_PATH.
DEFAULT_MODEL_PATH = os.environ.get(
    "FISHING_MODEL_PATH",
    os.path.join(os.path.dirname(__file__), "artifacts", "model.joblib"),
)

MIN_SAMPLES_TO_TRAIN = 30


def _build_model(kind: str):
    if kind == "xgboost":
        try:
            from xgboost import XGBClassifier

            return XGBClassifier(
                n_estimators=200,
                max_depth=4,
                learning_rate=0.1,
                subsample=0.9,
                eval_metric="logloss",
            )
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise SystemExit(
                "xgboost is not installed. `pip install xgboost` or omit --model."
            ) from exc

    from sklearn.ensemble import GradientBoostingClassifier

    return GradientBoostingClassifier(random_state=42)


def _logistic_fallback():
    from sklearn.linear_model import LogisticRegression

    return LogisticRegression(max_iter=1000)


def train(
    X: np.ndarray,
    y: np.ndarray,
    model_path: str = DEFAULT_MODEL_PATH,
    kind: str = "gboost",
) -> dict:
    """Train, evaluate, and persist a model. Returns a metrics dict."""
    from sklearn.metrics import accuracy_score, roc_auc_score
    from sklearn.model_selection import train_test_split

    n = len(y)
    if n < MIN_SAMPLES_TO_TRAIN:
        raise SystemExit(
            f"Only {n} samples available (need >= {MIN_SAMPLES_TO_TRAIN}). "
            "Collect more logged sessions or train with --synthetic."
        )

    classes = np.unique(y)
    if len(classes) < 2:
        raise SystemExit(
            "Training data has a single class — cannot fit a classifier yet. "
            "More varied outcomes are needed."
        )

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Small datasets favour the simpler linear model.
    model = _logistic_fallback() if n < 80 else _build_model(kind)
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    proba = model.predict_proba(X_test)[:, 1]
    accuracy = float(accuracy_score(y_test, preds))
    try:
        auc = float(roc_auc_score(y_test, proba))
    except ValueError:
        auc = float("nan")

    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    artifact = {
        "model": model,
        "feature_names": FEATURE_NAMES,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_samples": int(n),
        "metrics": {"accuracy": accuracy, "roc_auc": auc},
        "model_kind": type(model).__name__,
    }
    joblib.dump(artifact, model_path)

    metrics = {
        "accuracy": round(accuracy, 4),
        "roc_auc": None if np.isnan(auc) else round(auc, 4),
        "n_samples": int(n),
        "model_kind": type(model).__name__,
        "model_path": model_path,
    }
    return metrics


def generate_synthetic(n: int = 500, seed: int = 7) -> list[SessionContext]:
    """Generate plausible synthetic sessions for cold-start training/demo.

    The synthetic label is correlated with conditions the rule engine likes, so
    a model trained on it learns sensible structure before real data arrives.
    """
    from core.rules import score_session

    rng = np.random.default_rng(seed)
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    spots = ["Lake Verde", "River Bend", "Coastal Pier", "Mill Pond", "Blue Reservoir"]
    contexts: list[SessionContext] = []

    for _ in range(n):
        start = base + timedelta(
            days=int(rng.integers(0, 365)), hours=int(rng.integers(0, 24))
        )
        p0 = float(rng.normal(1015, 8))
        trend = float(rng.normal(0, 2.5))
        temp = float(rng.normal(18, 7))
        wind = float(abs(rng.normal(12, 8)))
        rain = float(max(0.0, rng.normal(-0.5, 1.5)))
        weather = [
            WeatherSnapshot(start - timedelta(hours=3), temp - trend, wind, p0, rain),
            WeatherSnapshot(start, temp, wind, p0 + trend, rain),
        ]
        ctx = SessionContext(
            location_text=spots[int(rng.integers(0, len(spots)))],
            start_time=start,
            weather=weather,
            catches=0,
        )
        # Label from the rule score plus moderate Gaussian noise, then
        # thresholded. This keeps outcomes realistically imperfect while
        # leaving a learnable relationship between conditions and success
        # (a pure Bernoulli draw at mid-range probabilities would be noise).
        score = score_session(ctx).total / 100.0
        noisy = score + float(rng.normal(0, 0.12))
        ctx.catches = 1 if noisy > 0.6 else 0
        contexts.append(ctx)

    return contexts


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the Fishing Copilot model")
    parser.add_argument(
        "--model",
        choices=["gboost", "xgboost"],
        default="gboost",
        help="Model family for larger datasets (default: gboost / sklearn).",
    )
    parser.add_argument(
        "--synthetic",
        type=int,
        default=0,
        metavar="N",
        help="Train on N generated sessions instead of the DB (cold start).",
    )
    parser.add_argument("--out", default=DEFAULT_MODEL_PATH, help="Artifact path.")
    args = parser.parse_args()

    if args.synthetic > 0:
        print(f"Generating {args.synthetic} synthetic sessions...")
        contexts = generate_synthetic(args.synthetic)
        X, y = build_dataset(contexts)
        n_sessions = len(contexts)
    else:
        from backend.app.db import SessionLocal

        print("Loading sessions from the backend database...")
        X, y, n_sessions = build_dataset_from_db(SessionLocal)

    print(f"Built dataset: {n_sessions} sessions, {len(FEATURE_NAMES)} features each.")
    metrics = train(X, y, model_path=args.out, kind=args.model)
    print("Training complete:")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
