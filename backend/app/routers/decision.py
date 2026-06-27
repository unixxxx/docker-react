"""GET /decision — the home-screen GO / DON'T GO / OPTIONAL answer."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as DBSession

from .. import llm
from ..db import get_db
from ..schemas import DecisionOut
from ..services import build_decision

router = APIRouter(tags=["decision"])


@router.get("/decision", response_model=DecisionOut)
async def get_decision(
    location: str = Query(..., description="Place name or 'lat,lon'"),
    db: DBSession = Depends(get_db),
):
    try:
        decision, label, summary, _ctx = await build_decision(db, location)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # weather/network failure
        raise HTTPException(status_code=502, detail=f"Weather lookup failed: {exc}") from exc

    explanation = await llm.generate_explanation(
        decision=decision.decision,
        probability=decision.probability,
        breakdown=decision.breakdown,
        weather_summary=summary,
    )

    return DecisionOut(
        location=label,
        decision=decision.decision,
        probability=decision.probability,
        final_score=decision.final_score,
        rule_score=decision.rule_score,
        ml_probability=decision.ml_probability,
        confidence=decision.confidence,
        explanation=explanation,
        time_windows=decision.time_windows,
        breakdown=decision.breakdown,
        model_used=decision.ml_probability is not None,
    )
