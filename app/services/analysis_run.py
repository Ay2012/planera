"""Shared analysis execution + inspection storage (used by /analyze and /chat)."""

from __future__ import annotations

from dataclasses import dataclass

from app.agent.graph import run_analysis
from app.api.workspace import store_inspection
from app.schemas import AnalyzeResponse, InspectionData


@dataclass(frozen=True)
class StoredAnalysisRun:
    """Result of a full analysis run including the built inspection payload."""

    response: AnalyzeResponse
    inspection: InspectionData


def run_stored_analysis(query: str) -> StoredAnalysisRun:
    """Run `run_analysis`, persist inspection to process memory, return API + inspection objects."""

    state = run_analysis(query)
    base = AnalyzeResponse(
        analysis=state["analysis"],
        trace=state.get("trace", []),
        executed_steps=state.get("executed_steps", []),
        errors=state.get("errors", []),
    )
    inspection_id, inspection = store_inspection(query, base)
    response = AnalyzeResponse(
        analysis=base.analysis,
        trace=base.trace,
        executed_steps=base.executed_steps,
        errors=base.errors,
        inspection_id=inspection_id,
    )
    return StoredAnalysisRun(response=response, inspection=inspection)
