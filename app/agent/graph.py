"""Workflow entrypoints for the staged analytics runtime implementation."""

from __future__ import annotations

from typing import Any

from app.agent._compat import raise_not_implemented


def run_analysis(query: str, source_ids: list[str] | None = None) -> dict[str, Any]:
    """Compatibility entrypoint used by the API service layer."""

    raise_not_implemented("End-to-end analysis graph")


def load_schema_context_node(state: dict[str, Any]) -> dict[str, Any]:
    """Load schema context into workflow state."""

    raise_not_implemented("Schema context graph node")


def planner_node(state: dict[str, Any]) -> dict[str, Any]:
    """Create the full ordered plan for the request."""

    raise_not_implemented("Planner graph node")


def query_writer_node(state: dict[str, Any]) -> dict[str, Any]:
    """Generate exactly one query for the current step."""

    raise_not_implemented("Query writer graph node")


def executor_node(state: dict[str, Any]) -> dict[str, Any]:
    """Execute the current step and store any successful output."""

    raise_not_implemented("Executor graph node")


def analyzer_node(state: dict[str, Any]) -> dict[str, Any]:
    """Produce the final answer or request a replan."""

    raise_not_implemented("Analyzer graph node")


def replan_node(state: dict[str, Any]) -> dict[str, Any]:
    """Request one bounded replan after analyzer or execution failure."""

    raise_not_implemented("Replan graph node")


def best_effort_node(state: dict[str, Any]) -> dict[str, Any]:
    """Return the final best-effort answer when retry limits are exhausted."""

    raise_not_implemented("Best-effort graph node")
