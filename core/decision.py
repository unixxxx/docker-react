"""Decision engine — the final GO / OPTIONAL / DON'T GO output.

Blends the ML probability with the rule-based score:

    final_score = 0.7 * (ML_probability * 100) + 0.3 * rule_score

When no ML model is available the blend collapses to the rule score alone, so
the product still produces a sensible answer on day one (cold-start) and
improves as the data flywheel turns.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .features import SessionContext
from .rules import RuleBreakdown, score_session

ML_WEIGHT = 0.7
RULE_WEIGHT = 0.3

# Decision band thresholds on the 0..100 final score.
GO_THRESHOLD = 70
OPTIONAL_THRESHOLD = 41


@dataclass
class TimeWindow:
    label: str
    start_hour: int
    end_hour: int

    def as_dict(self) -> dict:
        return {
            "label": self.label,
            "start": f"{self.start_hour:02d}:00",
            "end": f"{self.end_hour:02d}:00",
        }


@dataclass
class Decision:
    decision: str            # "GO" | "OPTIONAL" | "DON'T GO"
    probability: float       # 0..1 success probability used for the headline
    final_score: float       # 0..100 blended score
    rule_score: float        # 0..100 rule component
    ml_probability: float | None  # 0..1, or None when no model
    confidence: float        # 0..1 model confidence (1.0 for pure rules baseline)
    breakdown: dict          # rule component breakdown
    time_windows: list[dict] # best windows today

    def as_dict(self) -> dict:
        return {
            "decision": self.decision,
            "probability": round(self.probability, 3),
            "final_score": round(self.final_score, 1),
            "rule_score": round(self.rule_score, 1),
            "ml_probability": (
                round(self.ml_probability, 3) if self.ml_probability is not None else None
            ),
            "confidence": round(self.confidence, 3),
            "breakdown": self.breakdown,
            "time_windows": self.time_windows,
        }


def _band(final_score: float) -> str:
    if final_score >= GO_THRESHOLD:
        return "GO"
    if final_score >= OPTIONAL_THRESHOLD:
        return "OPTIONAL"
    return "DON'T GO"


def best_time_windows(ctx: SessionContext) -> list[TimeWindow]:
    """The classic dawn / dusk feeding windows, always surfaced for the day."""
    return [
        TimeWindow("Morning bite", 5, 8),
        TimeWindow("Evening bite", 18, 21),
    ]


def decide(
    ctx: SessionContext,
    ml_probability: float | None = None,
    ml_confidence: float | None = None,
) -> Decision:
    """Combine the rule engine and (optional) ML probability into a decision."""
    breakdown: RuleBreakdown = score_session(ctx)
    rule_score = breakdown.total

    if ml_probability is not None:
        final_score = ML_WEIGHT * (ml_probability * 100.0) + RULE_WEIGHT * rule_score
        probability = ml_probability
        confidence = ml_confidence if ml_confidence is not None else 0.6
    else:
        # No model yet — fall back entirely to the rule engine.
        final_score = rule_score
        probability = rule_score / 100.0
        confidence = 0.5  # rule-only baseline carries moderate confidence

    final_score = max(0.0, min(100.0, final_score))

    return Decision(
        decision=_band(final_score),
        probability=probability,
        final_score=final_score,
        rule_score=rule_score,
        ml_probability=ml_probability,
        confidence=confidence,
        breakdown=breakdown.as_dict(),
        time_windows=[w.as_dict() for w in best_time_windows(ctx)],
    )


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
