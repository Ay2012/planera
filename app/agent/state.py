"""Minimal workflow state helpers for the planner-input phase."""

from __future__ import annotations

from typing import Any, TypedDict


class AnalysisState(TypedDict, total=False):
    """Loose workflow state used by compatibility tests and wrappers."""

    query: str
    source_ids: list[str]
    dataset_context: dict[str, Any]
    planner_input: dict[str, Any] | None
    compiled_plan: dict[str, Any] | None
    analysis: str
    trace: list[dict[str, Any]]
    executed_steps: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    metric: str


def create_initial_state(query: str, source_ids: list[str] | None = None) -> AnalysisState:
    """Return a minimal mutable state payload for compatibility callers."""

    return AnalysisState(
        query=query,
        source_ids=list(source_ids or []),
        dataset_context={},
        planner_input=None,
        compiled_plan=None,
        analysis="",
        trace=[],
        executed_steps=[],
        errors=[],
        metric="",
    )
