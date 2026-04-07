"""Legacy placeholder kept importable during the planner-input phase."""

from __future__ import annotations

from app.agent._compat import raise_not_implemented


def __getattr__(name: str):
    raise_not_implemented(f"app.agent.recommender.{name}")
