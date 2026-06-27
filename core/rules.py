"""Rule-based scoring engine — the fallback when no ML model is available.

Produces a 0..100 "rule score" from weather + moon, plus a per-component
breakdown that the explanation layer can turn into human language.

    score = pressure_score
          + wind_score
          + time_of_day_score
          + temperature_score
          + moon_modifier
          - rain_penalty

Components are tuned so a neutral day lands in the OPTIONAL band (~40-69) and
genuinely good conditions push into GO (70-100).
"""

from __future__ import annotations

from dataclasses import dataclass

from .features import SessionContext, build_features


@dataclass
class RuleBreakdown:
    pressure_score: float
    wind_score: float
    time_of_day_score: float
    temperature_score: float
    moon_modifier: float
    rain_penalty: float

    @property
    def total(self) -> float:
        raw = (
            self.pressure_score
            + self.wind_score
            + self.time_of_day_score
            + self.temperature_score
            + self.moon_modifier
            - self.rain_penalty
        )
        return max(0.0, min(100.0, raw))

    def as_dict(self) -> dict[str, float]:
        return {
            "pressure_score": round(self.pressure_score, 1),
            "wind_score": round(self.wind_score, 1),
            "time_of_day_score": round(self.time_of_day_score, 1),
            "temperature_score": round(self.temperature_score, 1),
            "moon_modifier": round(self.moon_modifier, 1),
            "rain_penalty": round(self.rain_penalty, 1),
            "total": round(self.total, 1),
        }


def _pressure_score(pressure_trend: float) -> float:
    """Stable or gently falling pressure is best for feeding fish.

    Range ~0..25. A sharp rise (post-front) suppresses the bite.
    """
    if -1.0 <= pressure_trend <= 0.5:
        return 25.0  # stable / slight drop — ideal
    if pressure_trend < -1.0:
        # Falling pressure ahead of a front: still good, tapering off.
        return max(10.0, 25.0 + pressure_trend * 3.0)
    # Rising pressure: bite tends to shut down.
    return max(0.0, 18.0 - pressure_trend * 4.0)


def _wind_score(wind_speed: float) -> float:
    """A light ripple ("walleye chop") beats dead calm or a gale. Range ~0..20."""
    if wind_speed <= 3:
        return 10.0  # glassy calm — fish are spooky
    if wind_speed <= 18:
        return 20.0  # light-to-moderate breeze — prime
    if wind_speed <= 30:
        return 10.0
    return 3.0  # too rough to fish comfortably


def _time_of_day_score(hour: float) -> float:
    """Dawn and dusk are the classic feeding windows. Range ~0..20."""
    h = int(hour) % 24
    if 5 <= h <= 8 or 18 <= h <= 21:
        return 20.0  # golden hours
    if 9 <= h <= 11 or 16 <= h <= 17:
        return 12.0  # shoulder periods
    if 12 <= h <= 15:
        return 6.0  # midday lull
    return 4.0  # deep night


def _temperature_score(temperature: float) -> float:
    """Most freshwater species feed best in a comfortable mid range. Range ~0..15."""
    if 12 <= temperature <= 24:
        return 15.0
    if 6 <= temperature < 12 or 24 < temperature <= 30:
        return 9.0
    return 3.0  # extreme cold or heat


def _moon_modifier(solunar_strength: float) -> float:
    """Solunar boost near new/full moon. Range 0..15."""
    return 15.0 * solunar_strength


def _rain_penalty(rain_flag: float) -> float:
    """Active rain is a modest negative (light rain can actually help)."""
    return 8.0 if rain_flag >= 1.0 else 0.0


def score_features(feats: dict[str, float]) -> RuleBreakdown:
    """Score a pre-computed feature dict."""
    return RuleBreakdown(
        pressure_score=_pressure_score(feats.get("pressure_trend", 0.0)),
        wind_score=_wind_score(feats.get("wind_speed", 0.0)),
        time_of_day_score=_time_of_day_score(feats.get("hour_of_day", 0.0)),
        # temperature_delta is a trend, not an absolute; the absolute is passed
        # separately via the context. We approximate "comfortable" using the
        # latest temperature when available (injected as "temperature").
        temperature_score=_temperature_score(feats.get("temperature", 18.0)),
        moon_modifier=_moon_modifier(feats.get("solunar_strength", 0.0)),
        rain_penalty=_rain_penalty(feats.get("rain_flag", 0.0)),
    )


def score_session(ctx: SessionContext) -> RuleBreakdown:
    """Score a session context end-to-end."""
    feats = build_features(ctx)
    # Inject the latest absolute temperature for the comfort band, since the
    # canonical feature vector only carries the temperature *delta*.
    latest_temp = next(
        (w.temperature for w in reversed(ctx.weather) if w.temperature is not None),
        18.0,
    )
    feats["temperature"] = float(latest_temp)
    return score_features(feats)
