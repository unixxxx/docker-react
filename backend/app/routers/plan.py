"""POST /plan — LLM-generated, actionable fishing plan."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from .. import llm
from ..db import get_db
from ..schemas import PlanOut, PlanRequest
from ..services import build_decision

router = APIRouter(tags=["plan"])


@router.post("/plan", response_model=PlanOut)
async def create_plan(req: PlanRequest, db: DBSession = Depends(get_db)):
    try:
        decision, label, summary, _ctx = await build_decision(db, req.location)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Weather lookup failed: {exc}") from exc

    plan = await llm.generate_plan(
        location=label,
        fishing_type=req.fishing_type,
        skill_level=req.skill_level,
        decision=decision.decision,
        probability=decision.probability,
        breakdown=decision.breakdown,
        weather_summary=summary,
        time_windows=decision.time_windows,
    )

    return PlanOut(
        location=label,
        decision=decision.decision,
        probability=decision.probability,
        plan=plan,
        time_windows=decision.time_windows,
    )
