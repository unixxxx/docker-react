"""POST /session/start — open a session (auto-called when the app opens)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from .. import models
from ..db import get_db
from ..schemas import SessionOut, SessionStartRequest

router = APIRouter(tags=["session"])


def _get_or_create_user(db: DBSession, user_id: str | None) -> models.User:
    if user_id:
        user = db.get(models.User, user_id)
        if user:
            return user
    user = models.User(id=user_id) if user_id else models.User()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/session/start", response_model=SessionOut)
def start_session(req: SessionStartRequest, db: DBSession = Depends(get_db)):
    user = _get_or_create_user(db, req.user_id)
    session = models.Session(
        user_id=user.id,
        location_text=req.location,
        start_time=datetime.now(timezone.utc),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return SessionOut(
        id=session.id,
        user_id=session.user_id,
        location_text=session.location_text,
        start_time=session.start_time,
        end_time=session.end_time,
    )
