"""Open-Meteo weather + geocoding client.

Free, no API key. We fetch a short window of recent + current hourly readings
so the feature engine can compute a pressure trend, then cache the result per
location/hour to stay well within rate limits.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

import httpx

from core.features import WeatherSnapshot

from .config import get_settings

settings = get_settings()

# Simple in-process cache: key -> (expires_at_epoch, value).
_cache: dict[str, tuple[float, object]] = {}


def _cache_key(prefix: str, location: str) -> str:
    # Bucket by the current hour so each location refreshes hourly.
    hour = datetime.now(timezone.utc).strftime("%Y%m%d%H")
    return f"{prefix}:{location.strip().lower()}:{hour}"


def _cache_get(key: str):
    hit = _cache.get(key)
    if hit and hit[0] > time.time():
        return hit[1]
    return None


def _cache_set(key: str, value) -> None:
    _cache[key] = (time.time() + settings.weather_cache_ttl_seconds, value)


def _parse_latlon(location: str) -> tuple[float, float] | None:
    """Accept a raw 'lat,lon' string so callers can skip geocoding."""
    parts = location.split(",")
    if len(parts) == 2:
        try:
            return float(parts[0]), float(parts[1])
        except ValueError:
            return None
    return None


async def geocode(location: str) -> tuple[float, float, str]:
    """Resolve a place name (or 'lat,lon') to coordinates + a display label."""
    direct = _parse_latlon(location)
    if direct:
        return direct[0], direct[1], location

    key = _cache_key("geo", location)
    cached = _cache_get(key)
    if cached:
        return cached  # type: ignore[return-value]

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            settings.open_meteo_geocode_url,
            params={"name": location, "count": 1, "language": "en", "format": "json"},
        )
        resp.raise_for_status()
        data = resp.json()

    results = data.get("results") or []
    if not results:
        raise ValueError(f"Could not geocode location: {location!r}")

    top = results[0]
    name = top.get("name", location)
    country = top.get("country_code", "")
    label = f"{name}, {country}".strip(", ")
    value = (float(top["latitude"]), float(top["longitude"]), label)
    _cache_set(key, value)
    return value


async def fetch_weather(location: str) -> tuple[list[WeatherSnapshot], str]:
    """Return (recent->now hourly snapshots, resolved location label)."""
    lat, lon, label = await geocode(location)

    key = _cache_key("wx", f"{lat:.3f},{lon:.3f}")
    cached = _cache_get(key)
    if cached:
        return cached  # type: ignore[return-value]

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            settings.open_meteo_forecast_url,
            params={
                "latitude": lat,
                "longitude": lon,
                "hourly": "temperature_2m,surface_pressure,wind_speed_10m,precipitation",
                "past_days": 1,
                "forecast_days": 1,
                "timezone": "UTC",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])
    pressures = hourly.get("surface_pressure", [])
    winds = hourly.get("wind_speed_10m", [])
    rains = hourly.get("precipitation", [])

    now = datetime.now(timezone.utc)
    snapshots: list[WeatherSnapshot] = []
    for i, t in enumerate(times):
        ts = datetime.fromisoformat(t).replace(tzinfo=timezone.utc)
        if ts > now:
            break  # only keep readings up to and including the current hour
        snapshots.append(
            WeatherSnapshot(
                timestamp=ts,
                temperature=_at(temps, i),
                pressure=_at(pressures, i),
                wind_speed=_at(winds, i),
                rain=_at(rains, i),
            )
        )

    # Keep the most recent ~6 hours — enough to compute a meaningful trend.
    snapshots = snapshots[-6:] if len(snapshots) > 6 else snapshots
    if not snapshots:
        # Defensive: if the past window is empty, synthesize a neutral "now".
        snapshots = [WeatherSnapshot(timestamp=now)]

    value = (snapshots, label)
    _cache_set(key, value)
    return value


def _at(seq, i):
    try:
        v = seq[i]
        return None if v is None else float(v)
    except (IndexError, TypeError, ValueError):
        return None
