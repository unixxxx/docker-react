"""Service layer: orchestrates weather -> features -> ML -> decision.

Keeps the routers thin and ensures every endpoint computes the decision the
same way.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session as DBSession

from core.decision import Decision, decide
from core.features import SessionContext, WeatherSnapshot
from ml import inference

from . import models
from .weather import fetch_weather


def weather_summary(snapshots: list[WeatherSnapshot]) -> str:
    """Compact human-readable conditions string for prompts/UX."""
    if not snapshots:
        return "no recent data"
    latest = snapshots[-1]
    trend = 0.0
    pressures = [s.pressure for s in snapshots if s.pressure is not None]
    if len(pressures) >= 2:
        trend = pressures[-1] - pressures[0]
    trend_word = "rising" if trend > 0.5 else "falling" if trend < -0.5 else "stable"
    bits = []
    if latest.temperature is not None:
        bits.append(f"{latest.temperature:.0f}°C")
    if latest.wind_speed is not None:
        bits.append(f"wind {latest.wind_speed:.0f} km/h")
    if latest.pressure is not None:
        bits.append(f"pressure {latest.pressure:.0f} hPa ({trend_word})")
    if latest.rain is not None and latest.rain > 0.1:
        bits.append("rain")
    return ", ".join(bits) if bits else "mild conditions"


def persist_weather(db: DBSession, location_label: str, snapshots: list[WeatherSnapshot]) -> None:
    """Store the freshest snapshot for the location (feeds the flywheel)."""
    if not snapshots:
        return
    latest = snapshots[-1]
    exists = (
        db.query(models.WeatherSnapshot)
        .filter(
            models.WeatherSnapshot.location_text == location_label,
            models.WeatherSnapshot.timestamp == latest.timestamp,
        )
        .first()
    )
    if exists:
        return
    db.add(
        models.WeatherSnapshot(
            location_text=location_label,
            timestamp=latest.timestamp,
            temperature=latest.temperature,
            wind_speed=latest.wind_speed,
            pressure=latest.pressure,
            rain=latest.rain,
        )
    )
    db.commit()


async def build_decision(
    db: DBSession, location: str
) -> tuple[Decision, str, str, SessionContext]:
    """Fetch conditions and return (decision, location_label, summary, context)."""
    snapshots, label = await fetch_weather(location)
    ctx = SessionContext(
        location_text=label,
        start_time=datetime.now(timezone.utc),
        weather=snapshots,
        catches=0,
    )

    prediction = inference.predict(ctx)
    if prediction is not None:
        decision = decide(
            ctx,
            ml_probability=prediction.probability,
            ml_confidence=prediction.confidence,
        )
    else:
        decision = decide(ctx)

    persist_weather(db, label, snapshots)
    return decision, label, weather_summary(snapshots), ctx
