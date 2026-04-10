"""Planner-facing entrypoints for the staged analytics runtime implementation."""

from __future__ import annotations

from typing import Any

from app.agent._compat import raise_not_implemented
from app.llm import get_llm_client


def build_compact_schema_context(dataset_context: dict[str, Any], question: str) -> dict[str, Any]:
    """Return a compact schema/context summary for planning prompts."""

    raise_not_implemented("Compact schema/context builder")


def plan_analysis(state: dict[str, Any]) -> dict[str, Any]:
    """Return the planner-authored full workflow plan."""

    raise_not_implemented("Planner runtime")


def replan_analysis(state: dict[str, Any]) -> dict[str, Any]:
    """Return one revised workflow plan after failure."""

    raise_not_implemented("Planner replan runtime")


__all__ = ["build_compact_schema_context", "get_llm_client", "plan_analysis", "replan_analysis"]
