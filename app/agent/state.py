"""Typed workflow state for the compiled-plan analytics workflow."""

from __future__ import annotations

from typing import Any

from typing_extensions import TypedDict


class AnalysisState(TypedDict):
    """Explicit state carried through the analytics workflow."""

    query: str
    source_ids: list[str]
    dataset_context: dict[str, Any]
    intent: str
    metric: str
    planner_reasoning: str
    compiled_plan: dict[str, Any] | None
    repair_attempted: bool
    artifacts: dict[str, Any]
    executed_steps: list[dict[str, Any]]
    analysis: str
    total_steps: int
    last_error: dict[str, Any] | None
    workflow_status: str
    trace: list[dict[str, Any]]
    errors: list[dict[str, Any]]


def create_initial_state(query: str, source_ids: list[str] | None = None) -> AnalysisState:
    """Return the initial workflow state for a new request."""

    return AnalysisState(
        query=query,
        source_ids=list(source_ids or []),
        dataset_context={},
        intent="",
        metric="",
        planner_reasoning="",
        compiled_plan=None,
        repair_attempted=False,
        artifacts={},
        executed_steps=[],
        analysis="",
        total_steps=0,
        last_error=None,
        workflow_status="planning",
        trace=[],
        errors=[],
    )
