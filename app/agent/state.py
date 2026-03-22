"""Typed workflow state for the LangGraph planner-executor loop."""

from __future__ import annotations

from typing import Any

from typing_extensions import TypedDict


class AnalysisState(TypedDict):
    """Explicit state carried through the analytics workflow."""

    query: str
    dataset_context: dict[str, Any]
    intent: str
    metric: str
    planner_reasoning: str
    current_step: dict[str, Any] | None
    planner_action: str
    artifacts: dict[str, Any]
    executed_steps: list[dict[str, Any]]
    analysis: str
    retry_count: int
    max_retries: int
    total_steps: int
    max_steps: int
    last_error: dict[str, Any] | None
    loop_status: str
    trace: list[dict[str, Any]]
    errors: list[dict[str, Any]]


def create_initial_state(query: str) -> AnalysisState:
    """Return the initial workflow state for a new request."""

    return AnalysisState(
        query=query,
        dataset_context={},
        intent="",
        metric="",
        planner_reasoning="",
        current_step=None,
        planner_action="execute_step",
        artifacts={},
        executed_steps=[],
        analysis="",
        retry_count=0,
        max_retries=2,
        total_steps=0,
        max_steps=5,
        last_error=None,
        loop_status="planning",
        trace=[],
        errors=[],
    )
