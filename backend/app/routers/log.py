"""POST /log — record a catch result. This is the data-flywheel write path."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from .. import models
from ..db import get_db
from ..schemas import LogOut, LogRequest

router = APIRouter(tags=["log"])

_SUCCESS_VALUES = {"caught", "catch", "success", "1", "true", "yes"}


@router.post("/log", response_model=LogOut)
def log_result(req: LogRequest, db: DBSession = Depends(get_db)):
    session = db.get(models.Session, req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session_id not found")

    success = 1 if req.result.strip().lower() in _SUCCESS_VALUES else 0
    catch = models.Catch(
        session_id=session.id,
        timestamp=datetime.now(timezone.utc),
        bait=req.bait,
        success=success,
        notes=req.notes,
    )
    db.add(catch)
    # First log on a session also stamps its end_time (session is "live").
    if session.end_time is None:
        session.end_time = datetime.now(timezone.utc)
    db.commit()
    db.refresh(catch)

    return LogOut(
        id=catch.id,
        session_id=catch.session_id,
        success=catch.success,
        bait=catch.bait,
        notes=catch.notes,
        timestamp=catch.timestamp,
    )
