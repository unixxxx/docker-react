"""Feature engineering pipeline.

Turns a *session context* (location + time + a short history of weather
snapshots + any catches) into a fixed, ordered feature vector plus a binary
label. Used identically at training time (over stored sessions) and at
inference time (over a live forecast), which is what keeps the model honest.

The public surface:

- ``FEATURE_NAMES``         : canonical ordered list of feature keys
- ``build_features(ctx)``   : context -> ``dict`` of named features
- ``feature_vector(feats)`` : named features -> ordered ``list[float]``
- ``label_for_session(...)``: catches -> 0/1 success label
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone

from . import moon

# Canonical feature order. NEVER reorder without retraining — the model's
# coefficients are positional. Append-only if you must add features.
FEATURE_NAMES: list[str] = [
    "hour_of_day",
    "pressure_trend",
    "wind_speed",
    "temperature_delta",
    "rain_flag",
    "moon_illumination",
    "solunar_strength",
    "season",
    "day_of_week",
    "location_hash",
]

# Number of buckets the location hash is folded into. Small enough to be a
# usable categorical signal, large enough to separate distinct spots.
LOCATION_HASH_BUCKETS = 64


@dataclass
class WeatherSnapshot:
    """One observation of weather conditions at a location/time."""

    timestamp: datetime
    temperature: float | None = None  # degrees C
    wind_speed: float | None = None   # km/h
    pressure: float | None = None     # hPa
    rain: float | None = None         # mm in the hour


@dataclass
class SessionContext:
    """Everything the feature engine needs about one fishing session."""

    location_text: str
    start_time: datetime
    # Ordered oldest -> newest. The most recent snapshot is "now".
    weather: list[WeatherSnapshot] = field(default_factory=list)
    catches: int = 0  # number of successful catches in the session


def _season_from_month(month: int) -> int:
    """Northern-hemisphere meteorological season as an ordinal 0..3.

    0 = winter, 1 = spring, 2 = summer, 3 = autumn.
    """
    if month in (12, 1, 2):
        return 0
    if month in (3, 4, 5):
        return 1
    if month in (6, 7, 8):
        return 2
    return 3


def location_hash(location_text: str) -> int:
    """Stable bucketed hash of a location string.

    Uses md5 (not Python's salted ``hash``) so the value is identical across
    processes and runs — essential for reproducible training.
    """
    digest = hashlib.md5(location_text.strip().lower().encode("utf-8")).hexdigest()
    return int(digest, 16) % LOCATION_HASH_BUCKETS


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _pressure_trend(weather: list[WeatherSnapshot]) -> float:
    """Net pressure change across the window (hPa). Positive = rising."""
    readings = [w.pressure for w in weather if w.pressure is not None]
    if len(readings) < 2:
        return 0.0
    return float(readings[-1] - readings[0])


def _temperature_delta(weather: list[WeatherSnapshot]) -> float:
    readings = [w.temperature for w in weather if w.temperature is not None]
    if len(readings) < 2:
        return 0.0
    return float(readings[-1] - readings[0])


def _latest(weather: list[WeatherSnapshot], attr: str, default: float) -> float:
    for snap in reversed(weather):
        value = getattr(snap, attr)
        if value is not None:
            return float(value)
    return default


def build_features(ctx: SessionContext) -> dict[str, float]:
    """Compute the named feature dict for a session context."""
    start = _ensure_utc(ctx.start_time)
    rain_latest = _latest(ctx.weather, "rain", 0.0)

    feats = {
        "hour_of_day": float(start.hour),
        "pressure_trend": _pressure_trend(ctx.weather),
        "wind_speed": _latest(ctx.weather, "wind_speed", 0.0),
        "temperature_delta": _temperature_delta(ctx.weather),
        "rain_flag": 1.0 if rain_latest > 0.1 else 0.0,
        "moon_illumination": moon.illumination(start),
        "solunar_strength": moon.solunar_strength(start),
        "season": float(_season_from_month(start.month)),
        "day_of_week": float(start.weekday()),
        "location_hash": float(location_hash(ctx.location_text)),
    }
    return feats


def feature_vector(feats: dict[str, float]) -> list[float]:
    """Project a named feature dict onto the canonical ordered vector."""
    return [float(feats.get(name, 0.0)) for name in FEATURE_NAMES]


def label_for_session(catches: int) -> int:
    """Success label: 1 if any fish were caught in the session, else 0."""
    return 1 if catches and catches > 0 else 0


def build_example(ctx: SessionContext) -> tuple[list[float], int]:
    """Full training example: ``(feature_vector, label)``."""
    feats = build_features(ctx)
    return feature_vector(feats), label_for_session(ctx.catches)
