"""GET /history — a user's past sessions and catches."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as DBSession

from .. import models
from ..db import get_db
from ..schemas import CatchOut, HistoryOut, SessionHistoryOut

router = APIRouter(tags=["history"])


@router.get("/history", response_model=HistoryOut)
def get_history(
    user_id: str = Query(..., description="User id returned by /session/start"),
    limit: int = Query(50, ge=1, le=200),
    db: DBSession = Depends(get_db),
):
    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user_id not found")

    sessions = (
        db.query(models.Session)
        .filter(models.Session.user_id == user_id)
        .order_by(models.Session.start_time.desc())
        .limit(limit)
        .all()
    )

    out = [
        SessionHistoryOut(
            id=s.id,
            location_text=s.location_text,
            start_time=s.start_time,
            end_time=s.end_time,
            catches=[
                CatchOut(
                    id=c.id,
                    bait=c.bait,
                    success=c.success,
                    notes=c.notes,
                    timestamp=c.timestamp,
                )
                for c in s.catches
            ],
        )
        for s in sessions
    ]
    return HistoryOut(user_id=user_id, sessions=out)
