"""AI layer — LLM-powered fishing plans and prediction explanations.

Uses the Anthropic API (Claude) when ``ANTHROPIC_API_KEY`` is set, and falls
back to deterministic templates otherwise so the product works end-to-end with
zero configuration.

The LLM is used for exactly two jobs (per the design):
  A. Fishing Plan Generator  -> natural-language, actionable plan
  B. Explanation Engine       -> one-line "why" behind the prediction
"""

from __future__ import annotations

from .config import get_settings

settings = get_settings()

# Lazily-constructed async client so importing this module never requires the
# SDK or a key to be present.
_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    if not settings.anthropic_api_key:
        return None
    try:
        from anthropic import AsyncAnthropic

        _client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        return _client
    except ImportError:  # pragma: no cover - SDK optional
        return None


async def _complete(system: str, prompt: str) -> str | None:
    """Single-shot Claude completion. Returns None on any failure."""
    client = _get_client()
    if client is None:
        return None
    try:
        resp = await client.messages.create(
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
        text = "".join(parts).strip()
        return text or None
    except Exception:
        # Never let an LLM hiccup break the API — fall back to templates.
        return None


# --------------------------------------------------------------------------- #
# A. Fishing Plan Generator
# --------------------------------------------------------------------------- #
PLAN_SYSTEM = (
    "You are an expert fishing guide. Given conditions and a model's success "
    "prediction, write a short, concrete, actionable fishing plan. Be practical "
    "and specific. Use plain text with short sections: Where, Bait, Technique, "
    "Timing. Keep it under 180 words. Do not invent exact GPS spots; speak in "
    "general structure terms (drop-offs, weed edges, inlets, shade lines)."
)


async def generate_plan(
    *,
    location: str,
    fishing_type: str,
    skill_level: str,
    decision: str,
    probability: float,
    breakdown: dict,
    weather_summary: str,
    time_windows: list[dict],
) -> str:
    windows = ", ".join(f"{w['label']} {w['start']}-{w['end']}" for w in time_windows)
    prompt = (
        f"Location: {location}\n"
        f"Fishing type: {fishing_type}\n"
        f"Angler skill level: {skill_level}\n"
        f"Decision: {decision} (success probability {probability:.0%})\n"
        f"Conditions: {weather_summary}\n"
        f"Rule breakdown: {breakdown}\n"
        f"Best windows today: {windows}\n\n"
        "Write the fishing plan now."
    )
    text = await _complete(PLAN_SYSTEM, prompt)
    if text:
        return text
    return _fallback_plan(
        location, fishing_type, skill_level, decision, probability, time_windows
    )


def _fallback_plan(
    location: str,
    fishing_type: str,
    skill_level: str,
    decision: str,
    probability: float,
    time_windows: list[dict],
) -> str:
    windows = " and ".join(f"{w['start']}-{w['end']}" for w in time_windows)
    bait = {
        "fly": "match the local hatch — start with a nymph, switch to dry flies on rises",
        "surf": "fresh cut bait or a metal spoon worked through the wash",
    }.get(fishing_type, "soft plastics near structure, or live worm under a float")
    return (
        f"Plan for {location} ({fishing_type}, {skill_level}) — {decision}, "
        f"~{probability:.0%} success.\n\n"
        f"Where: Focus on structure — weed edges, drop-offs, and shade lines where "
        f"fish stage to feed.\n"
        f"Bait: Try {bait}.\n"
        f"Technique: Cover water with a slow, varied retrieve; slow down further if "
        f"the bite is tough.\n"
        f"Timing: Prioritise the feeding windows ({windows}); be on the water early."
    )


# --------------------------------------------------------------------------- #
# B. Explanation Engine
# --------------------------------------------------------------------------- #
EXPLAIN_SYSTEM = (
    "You explain a fishing-success prediction in ONE short, friendly sentence "
    "(max 25 words). Reference the strongest 1-2 factors (pressure, wind, time "
    "of day, moon, rain). No preamble, no lists — just the sentence."
)


async def generate_explanation(
    *,
    decision: str,
    probability: float,
    breakdown: dict,
    weather_summary: str,
) -> str:
    prompt = (
        f"Decision: {decision} ({probability:.0%} success)\n"
        f"Conditions: {weather_summary}\n"
        f"Score breakdown: {breakdown}\n\n"
        "Explain why in one sentence."
    )
    text = await _complete(EXPLAIN_SYSTEM, prompt)
    if text:
        return text
    return _fallback_explanation(decision, probability, breakdown)


def _fallback_explanation(decision: str, probability: float, breakdown: dict) -> str:
    drivers = []
    if breakdown.get("pressure_score", 0) >= 20:
        drivers.append("stable barometric pressure")
    if breakdown.get("time_of_day_score", 0) >= 18:
        drivers.append("a peak feeding window")
    if breakdown.get("moon_modifier", 0) >= 8:
        drivers.append("a strong solunar moon phase")
    if breakdown.get("rain_penalty", 0) > 0:
        drivers.append("active rain working against you")
    if breakdown.get("wind_score", 0) <= 3:
        drivers.append("rough wind")

    reason = ", ".join(drivers[:2]) if drivers else "mixed conditions"
    verb = {
        "GO": "Good odds thanks to",
        "OPTIONAL": "Conditions are mixed —",
        "DON'T GO": "Tough day due to",
    }.get(decision, "Conditions reflect")
    return f"{verb} {reason} ({probability:.0%} estimated success)."
