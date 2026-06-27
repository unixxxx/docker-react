"""SQLAlchemy ORM models — the ML-ready data schema.

Tables mirror the product spec: users, sessions, weather_snapshots, catches.
Kept deliberately flat and append-only so the nightly training job can replay
history cleanly.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)

    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    location_text = Column(String, nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), default=_now, nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="sessions")
    catches = relationship("Catch", back_populates="session", cascade="all, delete-orphan")


class WeatherSnapshot(Base):
    __tablename__ = "weather_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    location_text = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    temperature = Column(Float, nullable=True)   # degrees C
    wind_speed = Column(Float, nullable=True)     # km/h
    pressure = Column(Float, nullable=True)       # hPa
    rain = Column(Float, nullable=True)           # mm


class Catch(Base):
    __tablename__ = "catches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), default=_now, nullable=False)
    bait = Column(String, nullable=True)
    success = Column(Integer, nullable=False, default=0)  # 1 = caught, 0 = no bite
    notes = Column(Text, nullable=True)

    session = relationship("Session", back_populates="catches")
