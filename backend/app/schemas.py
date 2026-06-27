"""Pydantic request/response models for the API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# --- /decision ---
class TimeWindowOut(BaseModel):
    label: str
    start: str
    end: str


class DecisionOut(BaseModel):
    location: str
    decision: str = Field(description="GO | OPTIONAL | DON'T GO")
    probability: float = Field(ge=0, le=1)
    final_score: float
    rule_score: float
    ml_probability: float | None
    confidence: float
    explanation: str
    time_windows: list[TimeWindowOut]
    breakdown: dict
    model_used: bool


# --- /plan ---
class PlanRequest(BaseModel):
    location: str
    fishing_type: str = Field(default="freshwater", description="e.g. freshwater, fly, surf")
    skill_level: str = Field(default="beginner", description="beginner | intermediate | expert")


class PlanOut(BaseModel):
    location: str
    decision: str
    probability: float
    plan: str
    time_windows: list[TimeWindowOut]


# --- /log ---
class LogRequest(BaseModel):
    session_id: str
    result: str = Field(description="caught | no_bite")
    bait: str | None = None
    notes: str | None = None


class LogOut(BaseModel):
    id: int
    session_id: str
    success: int
    bait: str | None
    notes: str | None
    timestamp: datetime


# --- /session ---
class SessionStartRequest(BaseModel):
    location: str
    user_id: str | None = None


class SessionOut(BaseModel):
    id: str
    user_id: str
    location_text: str
    start_time: datetime
    end_time: datetime | None


# --- /history ---
class CatchOut(BaseModel):
    id: int
    bait: str | None
    success: int
    notes: str | None
    timestamp: datetime


class SessionHistoryOut(BaseModel):
    id: str
    location_text: str
    start_time: datetime
    end_time: datetime | None
    catches: list[CatchOut]


class HistoryOut(BaseModel):
    user_id: str
    sessions: list[SessionHistoryOut]
