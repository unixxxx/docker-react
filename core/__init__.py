"""Fishing Copilot — shared domain core.

Pure-Python, dependency-light modules used by both the backend service and the
ML pipeline:

- ``moon``     : moon-phase calculation (no external API)
- ``features`` : feature engineering (session context -> feature vector + label)
- ``rules``    : rule-based scoring engine (the ML fallback)
- ``decision`` : final decision engine combining ML + rules

Keeping this logic in one place guarantees that training-time features and
inference-time features are computed identically — the single most important
property for an ML system that improves over time.
"""

from . import moon, features, rules, decision  # noqa: F401

__all__ = ["moon", "features", "rules", "decision"]
