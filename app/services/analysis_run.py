"""Shared analytics workflow invocation and in-process inspection materialization.

``run_stored_analysis`` backs both HTTP entry points:

- **Product:** ``POST /chat`` (auth, SQLite history, persisted inspection snapshots).
- **Debug:** ``POST /analyze`` (no auth, no DB; inspection id valid only in-memory for that process).

Both return the same ``AnalyzeResponse`` shape for the HTTP layer; only routing and persistence differ.
"""

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


def run_stored_analysis(query: str, source_ids: list[str] | None = None) -> StoredAnalysisRun:
    """Run `run_analysis`, persist inspection to process memory, return API + inspection objects."""

    state = run_analysis(query, source_ids=source_ids)
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
