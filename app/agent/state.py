"""Workflow state helpers for the schema-grounded multi-agent analytics flow."""

from __future__ import annotations

from typing import Any

from typing_extensions import TypedDict


class AnalysisState(TypedDict, total=False):
    """Explicit mutable state carried through the analytics workflow."""

    query: str
    source_ids: list[str]
    dataset_context: dict[str, Any]
    schema_context_summary: dict[str, Any]
    current_plan: dict[str, Any] | None
    current_step_index: int
    stored_outputs: dict[str, Any]
    step_queries: dict[str, list[str]]
    failure_history: dict[str, list[dict[str, Any]]]
    retry_counts: dict[str, int]
    replan_count: int
    analyzer_result: dict[str, Any] | None
    final_answer: str
    failure_summary: str
    workflow_status: str
    trace: list[dict[str, Any]]
    executed_steps: list[dict[str, Any]]
    errors: list[dict[str, Any]]


def create_initial_state(query: str, source_ids: list[str] | None = None) -> AnalysisState:
    """Return the initial workflow state for a new request."""

    return AnalysisState(
        query=query,
        source_ids=list(source_ids or []),
        dataset_context={},
        schema_context_summary={},
        current_plan=None,
        current_step_index=0,
        stored_outputs={},
        step_queries={},
        failure_history={},
        retry_counts={},
        replan_count=0,
        analyzer_result=None,
        final_answer="",
        failure_summary="",
        workflow_status="initializing",
        trace=[],
        executed_steps=[],
        errors=[],
    )
