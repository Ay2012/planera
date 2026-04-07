"""Compatibility graph entrypoints for the planner-input phase."""

from __future__ import annotations

from typing import Any

from app.agent._compat import raise_not_implemented


def run_analysis(query: str, source_ids: list[str] | None = None) -> dict[str, Any]:
    """Compatibility stub for the historical end-to-end analysis graph."""

    raise_not_implemented("End-to-end analysis graph")


def load_schema_context_node(state: dict[str, Any]) -> dict[str, Any]:
    """Compatibility stub for the historical schema-loading node."""

    raise_not_implemented("Schema context graph node")


def planner_compiled_node(state: dict[str, Any]) -> dict[str, Any]:
    """Compatibility stub for the historical planner node."""

    raise_not_implemented("Planner graph node")


def execute_plan_node(state: dict[str, Any]) -> dict[str, Any]:
    """Compatibility stub for the historical executor node."""

    raise_not_implemented("Executor graph node")


def analysis_node(state: dict[str, Any]) -> dict[str, Any]:
    """Compatibility stub for the historical analysis node."""

    raise_not_implemented("Analysis graph node")
