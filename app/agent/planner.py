"""Planner-facing public entrypoints.

This phase only supports constructing the full raw-schema planner input from uploaded
sources. Prompt rendering, LLM calls, SQL planning, and repair flows are deferred.
"""

from __future__ import annotations

from typing import Any

from app.agent._compat import raise_not_implemented
from app.data.planner_input import build_planner_input as _build_planner_input
from app.schemas import PlannerInput


def build_planner_input(query: str, source_ids: list[str] | None = None) -> PlannerInput:
    """Build the planner-facing raw schema contract for attached uploads."""

    return _build_planner_input(query, source_ids=source_ids)


def get_llm_client() -> Any:
    """Compatibility stub for the historical planner runtime."""

    raise_not_implemented("Planner LLM access")


def plan_compiled_query(state: dict[str, Any]) -> dict[str, Any]:
    """Compatibility stub for the historical compiled planner workflow."""

    raise_not_implemented("Compiled planner runtime")


def repair_failed_step(state: dict[str, Any], failed_step: dict[str, Any]) -> dict[str, Any]:
    """Compatibility stub for historical planner repair behavior."""

    raise_not_implemented("Planner repair runtime")


def _schema_subset_for_question(schema_manifest: dict[str, Any], question: str) -> dict[str, Any]:
    """Compatibility stub for the historical trimmed-schema planner input."""

    raise_not_implemented("Trimmed schema subsets")
