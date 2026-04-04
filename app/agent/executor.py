"""Execution engine for compiled SQL plans and legacy pandas helpers."""

from __future__ import annotations

from typing import Any, Literal

import duckdb
import pandas as pd

from app.agent.state import AnalysisState
from app.data.semantic_model import get_semantic_context, new_duckdb_connection
from app.schemas import ArtifactSummary, CompiledPlanStep, ExecutedStep


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


def _empty_table_failure(artifact: ArtifactSummary) -> bool:
    return artifact.artifact_type == "table" and artifact.row_count == 0


def compiled_plan_row_to_internal(row: dict[str, Any] | CompiledPlanStep) -> dict[str, Any]:
    """Map a compiled plan step to the executor shape used by `_execute_sql`."""

    if isinstance(row, CompiledPlanStep):
        row = row.model_dump()
    sid = row["id"]
    alias = row.get("output_alias") or f"step_{sid}"
    return {
        "id": str(sid),
        "kind": "sql",
        "purpose": row["purpose"],
        "code": row["query"],
        "output_alias": alias,
    }


def preflight_compiled_plan(state: AnalysisState, compiled_plan: dict[str, Any]) -> dict[str, Any]:
    """
    Validate compiled SQL steps against the active runtime before execution.

    Steps are checked in order so later queries can reference earlier output aliases.
    """

    conn = new_duckdb_connection()
    _register_artifacts(conn, state)
    rows = list(compiled_plan.get("plan") or [])
    rows.sort(key=lambda r: r["id"] if isinstance(r, dict) else r.id)

    for row in rows:
        internal = compiled_plan_row_to_internal(row)
        sql = internal["code"].strip().rstrip(";")
        try:
            preview = conn.execute(f"SELECT * FROM ({sql}) AS __planera_preflight LIMIT 0").fetchdf()
            conn.register(internal["output_alias"], preview)
        except Exception as exc:
            return {
                "status": "failed",
                "failed_step_id": internal["id"],
                "error": str(exc),
                "query": internal["code"],
            }

    return {"status": "success"}


def _try_sql_step(
    state: AnalysisState,
    internal: dict[str, Any],
    attempt: int,
) -> tuple[Literal["success", "failed"], ExecutedStep]:
    """Run one SQL step with post-execution validation (non-empty table)."""

    state["total_steps"] += 1
    try:
        artifact = _execute_sql(state, internal)
        if _empty_table_failure(artifact):
            state["artifacts"].pop(internal["output_alias"], None)
            raise ValueError("Step returned an empty result set.")
        executed = ExecutedStep(
            id=internal["id"],
            kind="sql",
            purpose=internal["purpose"],
            code=internal["code"],
            output_alias=internal["output_alias"],
            attempt=attempt,
            status="success",
            artifact=artifact,
        )
        state["executed_steps"].append(executed.model_dump())
        state["last_error"] = None
        return "success", executed
    except Exception as exc:
        executed = ExecutedStep(
            id=internal["id"],
            kind="sql",
            purpose=internal["purpose"],
            code=internal["code"],
            output_alias=internal["output_alias"],
            attempt=attempt,
            status="failed",
            error=str(exc),
        )
        state["executed_steps"].append(executed.model_dump())
        state["last_error"] = {"step_id": internal["id"], "message": str(exc), "code": internal["code"]}
        return "failed", executed


def execute_plan(state: AnalysisState, compiled_plan: dict[str, Any]) -> dict[str, Any]:
    """
    Iterate compiled plan steps in order: validate via execute + empty-table check.
    No LLM calls. On first failure, stop and return structured status.
    """

    rows = list(compiled_plan.get("plan") or [])
    rows.sort(key=lambda r: r["id"] if isinstance(r, dict) else r.id)

    for row in rows:
        internal = compiled_plan_row_to_internal(row)
        status, _ = _try_sql_step(state, internal, attempt=1)
        if status == "failed":
            sid = internal["id"]
            return {
                "status": "failed",
                "failed_step_id": sid,
                "error": state["last_error"]["message"] if state["last_error"] else "Unknown error",
            }

    return {"status": "success"}


def execute_single_plan_step(
    state: AnalysisState,
    compiled_step: dict[str, Any],
    attempt: int,
) -> dict[str, Any]:
    """Re-run a single compiled step (e.g. after repair)."""

    internal = compiled_plan_row_to_internal(compiled_step)
    status, _ = _try_sql_step(state, internal, attempt=attempt)
    if status == "failed":
        return {
            "status": "failed",
            "failed_step_id": internal["id"],
            "error": state["last_error"]["message"] if state["last_error"] else "Unknown error",
        }
    return {"status": "success"}
