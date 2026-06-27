"""Build an ML-ready dataset from stored sessions.

The backend persists sessions, weather snapshots, and catches. This module
joins them into ``SessionContext`` objects and runs them through the shared
feature engine so that training features are *byte-for-byte* what inference
will see.

It can read directly from the SQLite/Postgres database used by the backend, or
accept already-loaded rows for testing.
"""

from __future__ import annotations

from datetime import datetime

import numpy as np

from core.features import (
    FEATURE_NAMES,
    SessionContext,
    WeatherSnapshot,
    build_example,
)


def _parse_dt(value) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def context_from_rows(session_row: dict, weather_rows: list[dict], catch_rows: list[dict]) -> SessionContext:
    """Assemble a ``SessionContext`` from raw DB rows."""
    weather = [
        WeatherSnapshot(
            timestamp=_parse_dt(w["timestamp"]),
            temperature=w.get("temperature"),
            wind_speed=w.get("wind_speed"),
            pressure=w.get("pressure"),
            rain=w.get("rain"),
        )
        for w in sorted(weather_rows, key=lambda w: str(w["timestamp"]))
    ]
    successes = sum(1 for c in catch_rows if int(c.get("success", 0)) == 1)
    return SessionContext(
        location_text=session_row["location_text"],
        start_time=_parse_dt(session_row["start_time"]),
        weather=weather,
        catches=successes,
    )


def build_dataset(contexts: list[SessionContext]) -> tuple[np.ndarray, np.ndarray]:
    """Turn session contexts into ``(X, y)`` arrays."""
    X: list[list[float]] = []
    y: list[int] = []
    for ctx in contexts:
        vec, label = build_example(ctx)
        X.append(vec)
        y.append(label)
    return np.asarray(X, dtype=float), np.asarray(y, dtype=int)


def build_dataset_from_db(session_factory) -> tuple[np.ndarray, np.ndarray, int]:
    """Load every session from the DB and build ``(X, y, n_sessions)``.

    ``session_factory`` is a callable returning a SQLAlchemy session (the
    backend's ``SessionLocal``). Imported lazily so the ML package has no hard
    dependency on the backend being importable in every environment.
    """
    from backend.app import models  # local import to avoid a hard dependency

    db = session_factory()
    try:
        contexts: list[SessionContext] = []
        sessions = db.query(models.Session).all()
        for s in sessions:
            weather = (
                db.query(models.WeatherSnapshot)
                .filter(models.WeatherSnapshot.location_text == s.location_text)
                .all()
            )
            catches = (
                db.query(models.Catch).filter(models.Catch.session_id == s.id).all()
            )
            ctx = SessionContext(
                location_text=s.location_text,
                start_time=s.start_time,
                weather=[
                    WeatherSnapshot(
                        timestamp=w.timestamp,
                        temperature=w.temperature,
                        wind_speed=w.wind_speed,
                        pressure=w.pressure,
                        rain=w.rain,
                    )
                    for w in weather
                ],
                catches=sum(1 for c in catches if c.success == 1),
            )
            contexts.append(ctx)
        X, y = build_dataset(contexts)
        return X, y, len(contexts)
    finally:
        db.close()


__all__ = [
    "FEATURE_NAMES",
    "context_from_rows",
    "build_dataset",
    "build_dataset_from_db",
]
