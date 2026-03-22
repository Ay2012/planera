"""Execution engine for planner-emitted SQL and pandas steps."""

from __future__ import annotations

from typing import Any

import duckdb
import pandas as pd

from app.agent.state import AnalysisState
from app.data.semantic_model import get_semantic_context, new_duckdb_connection
from app.schemas import ArtifactSummary, ExecutedStep


SAFE_BUILTINS: dict[str, Any] = {
    "len": len,
    "min": min,
    "max": max,
    "sum": sum,
    "round": round,
    "sorted": sorted,
}


def _summarize_artifact(alias: str, value: Any) -> ArtifactSummary:
    if isinstance(value, pd.Series):
        value = value.to_frame()

    if isinstance(value, pd.DataFrame):
        preview_rows = value.head(5).where(pd.notnull(value), None).to_dict(orient="records")
        summary: dict[str, Any] = {}
        numeric = value.select_dtypes(include=["number"])
        if not numeric.empty:
            summary["numeric_means"] = numeric.mean().round(2).to_dict()
        return ArtifactSummary(
            alias=alias,
            artifact_type="table",
            row_count=int(len(value)),
            columns=list(value.columns),
            preview_rows=preview_rows,
            summary=summary,
        )

    if isinstance(value, (int, float, str, bool)):
        return ArtifactSummary(
            alias=alias,
            artifact_type="scalar" if not isinstance(value, str) else "text",
            row_count=1,
            columns=["value"],
            preview_rows=[{"value": value}],
            summary={"value": value},
        )

    return ArtifactSummary(alias=alias, artifact_type="unknown")


def _register_artifacts(conn: duckdb.DuckDBPyConnection, state: AnalysisState) -> None:
    for alias, artifact in state["artifacts"].items():
        if isinstance(artifact, pd.DataFrame):
            conn.register(alias, artifact)


def _execute_sql(state: AnalysisState, step: dict[str, Any]) -> ArtifactSummary:
    conn = new_duckdb_connection()
    _register_artifacts(conn, state)
    frame = conn.execute(step["code"]).fetchdf()
    state["artifacts"][step["output_alias"]] = frame
    return _summarize_artifact(step["output_alias"], frame)


def _execute_pandas(state: AnalysisState, step: dict[str, Any]) -> ArtifactSummary:
    context = get_semantic_context()
    local_env: dict[str, Any] = {
        **context.raw_views,
        **context.semantic_views,
        **state["artifacts"],
        "pd": pd,
        "result": None,
    }
    exec(step["code"], {"__builtins__": SAFE_BUILTINS}, local_env)
    result = local_env.get("result")
    if result is None:
        raise ValueError("Pandas step did not assign a `result` variable.")
    state["artifacts"][step["output_alias"]] = result
    return _summarize_artifact(step["output_alias"], result)


def execute_current_step(state: AnalysisState) -> AnalysisState:
    """Execute the step chosen by the planner."""

    step = state["current_step"]
    if step is None:
        raise ValueError("No current step available for execution.")

    state["total_steps"] += 1
    attempt = state["retry_count"] + 1
    try:
        artifact = _execute_sql(state, step) if step["kind"] == "sql" else _execute_pandas(state, step)
        executed = ExecutedStep(
            id=step["id"],
            kind=step["kind"],
            purpose=step["purpose"],
            code=step["code"],
            output_alias=step["output_alias"],
            attempt=attempt,
            status="success",
            artifact=artifact,
        )
        state["executed_steps"].append(executed.model_dump())
        state["last_error"] = None
        state["loop_status"] = "step_succeeded"
        return state
    except Exception as exc:
        executed = ExecutedStep(
            id=step["id"],
            kind=step["kind"],
            purpose=step["purpose"],
            code=step["code"],
            output_alias=step["output_alias"],
            attempt=attempt,
            status="failed",
            error=str(exc),
        )
        state["executed_steps"].append(executed.model_dump())
        state["last_error"] = {"step_id": step["id"], "message": str(exc), "code": step["code"]}
        state["loop_status"] = "step_failed"
        return state
