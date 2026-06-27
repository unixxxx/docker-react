"""Moon-phase calculation.

A small, self-contained astronomical approximation — no external API needed.
Accurate to well within a day for fishing purposes, which is all the solunar
heuristics require.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

# Mean length of the synodic month (new moon -> new moon), in days.
SYNODIC_MONTH = 29.53058867

# A known reference new moon: 2000-01-06 18:14 UTC.
_REFERENCE_NEW_MOON = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)

_PHASE_NAMES = [
    "New Moon",
    "Waxing Crescent",
    "First Quarter",
    "Waxing Gibbous",
    "Full Moon",
    "Waning Gibbous",
    "Last Quarter",
    "Waning Crescent",
]


def _ensure_utc(dt: datetime | None) -> datetime:
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def moon_age_days(dt: datetime | None = None) -> float:
    """Days since the most recent new moon (0 .. ~29.53)."""
    dt = _ensure_utc(dt)
    elapsed = (dt - _REFERENCE_NEW_MOON).total_seconds() / 86400.0
    return elapsed % SYNODIC_MONTH


def phase_fraction(dt: datetime | None = None) -> float:
    """Cyclic phase in [0, 1): 0 = new, 0.5 = full, ->1 wraps back to new."""
    return moon_age_days(dt) / SYNODIC_MONTH


def illumination(dt: datetime | None = None) -> float:
    """Illuminated fraction of the disk in [0, 1] (0 = new, 1 = full)."""
    return (1.0 - math.cos(2.0 * math.pi * phase_fraction(dt))) / 2.0


def phase_name(dt: datetime | None = None) -> str:
    """Human-readable phase name."""
    index = int((phase_fraction(dt) * 8) + 0.5) % 8
    return _PHASE_NAMES[index]


def solunar_strength(dt: datetime | None = None) -> float:
    """How strong the solunar influence is, in [0, 1].

    Fish feeding activity is widely held to peak around the new and full moons
    (the "major" solunar periods) and dip at the quarters. We map proximity to
    new/full onto a smooth 0..1 strength using the illuminated fraction's
    distance from the half-lit quarters.
    """
    illum = illumination(dt)
    # illum is 0 at new, 1 at full, 0.5 at quarters. Strength peaks at both
    # extremes and bottoms out at the quarters.
    return abs(illum - 0.5) * 2.0


def describe(dt: datetime | None = None) -> dict:
    """Convenience bundle used by the feature engine and explanations."""
    dt = _ensure_utc(dt)
    return {
        "phase_name": phase_name(dt),
        "phase_fraction": round(phase_fraction(dt), 4),
        "illumination": round(illumination(dt), 4),
        "solunar_strength": round(solunar_strength(dt), 4),
        "age_days": round(moon_age_days(dt), 2),
    }
