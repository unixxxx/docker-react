"""Fishing Copilot — FastAPI monolith entrypoint.

A single service that serves predictions, stores sessions, fetches weather +
moon data, runs ML inference, calls the LLM, and can trigger training.

Run from the repository root so the shared ``core`` and ``ml`` packages import:

    uvicorn backend.app.main:app --reload
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ml import inference

from .config import get_settings
from .db import SessionLocal, init_db
from .routers import decision, history, log, plan, session

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Should I go fishing right now — and what should I do?",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


# --- Feature routers ---
app.include_router(decision.router)
app.include_router(plan.router)
app.include_router(log.router)
app.include_router(history.router)
app.include_router(session.router)


# --- Ops / meta endpoints ---
meta = APIRouter(tags=["meta"])


@meta.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name}


@meta.get("/model/info")
def model_info():
    info = inference.model_info()
    return {
        "model_available": info is not None,
        "info": info,
        "note": "Falls back to the rule engine when no model is trained.",
    }


def _run_training() -> None:
    """Background training job (the nightly flywheel step)."""
    from ml.dataset import build_dataset_from_db
    from ml.train import train

    X, y, n = build_dataset_from_db(SessionLocal)
    if n == 0:
        return
    try:
        train(X, y)
    except SystemExit:
        # Not enough data / single class yet — expected early on.
        pass


@meta.post("/train")
def trigger_training(background: BackgroundTasks):
    """Kick off model retraining from logged sessions (non-blocking)."""
    background.add_task(_run_training)
    return {"status": "training_started"}


app.include_router(meta)
