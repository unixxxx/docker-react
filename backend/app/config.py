"""Application configuration, sourced from environment variables / .env."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Load from either the repo root or backend/.env (run uvicorn from root).
    model_config = SettingsConfigDict(env_file=(".env", "backend/.env"), extra="ignore")

    # --- Core ---
    app_name: str = "Fishing Copilot API"
    database_url: str = "sqlite:///./fishing_copilot.db"

    # --- LLM (Anthropic) ---
    # If unset, the AI layer degrades gracefully to deterministic templates.
    anthropic_api_key: str | None = None
    llm_model: str = "claude-opus-4-8"
    llm_max_tokens: int = 1024

    # --- Weather ---
    open_meteo_forecast_url: str = "https://api.open-meteo.com/v1/forecast"
    open_meteo_geocode_url: str = "https://geocoding-api.open-meteo.com/v1/search"
    weather_cache_ttl_seconds: int = 3600  # cache per location/hour

    # --- CORS ---
    cors_origins: list[str] = ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
