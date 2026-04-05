"""Execution engine for compiled SQL plans and legacy pandas helpers."""

from __future__ import annotations

from typing import Any, Literal

import duckdb
import pandas as pd

from app.agent.metric_aliases import canonical_metric_alias, canonical_metric_aliases, canonicalize_sql_metric_aliases
from app.agent.state import AnalysisState
from app.data.semantic_model import get_semantic_context, new_duckdb_connection
from app.schemas import ArtifactSummary, CompiledPlanStep, ExecutedStep, StepExpectation


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


def _execute_sql(state: AnalysisState, step: dict[str, Any]) -> pd.DataFrame:
    conn = new_duckdb_connection()
    _register_artifacts(conn, state)
    return conn.execute(step["code"]).fetchdf()


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
    expectation = _as_expectation(row["expectation"])
    expectation.expected_metric_columns = canonical_metric_aliases(expectation.expected_metric_columns)
    return {
        "id": str(sid),
        "kind": "sql",
        "purpose": row["purpose"],
        "code": canonicalize_sql_metric_aliases(row["query"]),
        "expectation": expectation,
        "output_alias": alias,
    }


def _as_expectation(value: dict[str, Any] | StepExpectation) -> StepExpectation:
    if isinstance(value, StepExpectation):
        return value
    return StepExpectation.model_validate(value)


def _missing_expected_columns(columns: list[str], expectation: StepExpectation) -> list[str]:
    present = {canonical_metric_alias(column) for column in columns}
    expected_columns = [
        *expectation.expected_grouping_columns,
        *canonical_metric_aliases(expectation.expected_metric_columns),
        *( [expectation.expected_period_column] if expectation.expected_period_column else [] ),
    ]
    seen: set[str] = set()
    missing: list[str] = []
    for column in expected_columns:
        if not column or column in seen:
            continue
        seen.add(column)
        if column not in present:
            missing.append(column)
    return missing


def _normalized_validation_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a validation-safe frame with duplicate column names removed."""

    if frame.columns.is_unique:
        return frame
    return frame.loc[:, ~frame.columns.duplicated()].copy()


def _effective_grouping_columns(expectation: StepExpectation) -> list[str]:
    """Return grouping columns relevant for comparison, excluding the period column itself."""

    seen: set[str] = set()
    result: list[str] = []
    for column in expectation.expected_grouping_columns:
        if not column or column == expectation.expected_period_column or column in seen:
            continue
        seen.add(column)
        result.append(column)
    return result


def _validate_step_expectation(expectation: StepExpectation) -> str | None:
    if expectation.step_category == "premise_check" and not expectation.expected_metric_columns:
        return "Premise-check steps must declare at least one expected metric column."
    if expectation.step_category == "premise_check" and expectation.comparison_type != "period_comparison":
        return "Premise-check steps must use period_comparison expectations."
    if expectation.comparison_type == "period_comparison" and not expectation.expected_period_column:
        return "Period comparison steps must declare an expected period column."
    if expectation.comparison_type == "grouped_breakdown" and not expectation.expected_grouping_columns:
        return "Grouped breakdown steps must declare expected grouping columns."
    if expectation.requires_distinct_periods and not expectation.expected_period_column:
        return "Distinct-period validation requires an expected period column."
    if expectation.min_expected_rows < 1:
        return "Step expectations must require at least one result row."
    return None


def _validate_preview_shape(
    internal: dict[str, Any],
    preview_columns: list[str],
    original_expectation: StepExpectation | None = None,
) -> str | None:
    expectation = _as_expectation(internal["expectation"])
    if original_expectation is not None and expectation.model_dump() != original_expectation.model_dump():
        return "The repaired step changed the expected output shape."
    expectation_error = _validate_step_expectation(expectation)
    if expectation_error:
        return expectation_error

    missing = _missing_expected_columns(preview_columns, expectation)
    if missing:
        return f"The step preview is missing expected columns: {', '.join(missing)}."
    return None


def _validate_result_shape(frame: pd.DataFrame, internal: dict[str, Any]) -> tuple[str, str | None]:
    expectation = _as_expectation(internal["expectation"])
    frame = _normalized_validation_frame(frame)
    expectation_error = _validate_step_expectation(expectation)
    if expectation_error:
        return "invalid", expectation_error

    if frame.empty:
        return "invalid", "The step returned no rows."

    missing = _missing_expected_columns(list(frame.columns), expectation)
    if missing:
        return "invalid", f"The result is missing expected columns: {', '.join(missing)}."

    if expectation.requires_distinct_periods and expectation.expected_period_column:
        distinct_periods = frame[expectation.expected_period_column].dropna().astype(str).nunique()
        if distinct_periods < 2:
            return "invalid", "The comparison result did not return at least two comparable periods."
        effective_grouping_columns = _effective_grouping_columns(expectation)
        if expectation.step_category == "premise_check" and not effective_grouping_columns:
            if distinct_periods != len(frame):
                return "invalid", "The premise-check result did not preserve one comparable row per period."
        if effective_grouping_columns:
            comparable_columns = [*effective_grouping_columns, expectation.expected_period_column]
            comparable_frame = frame[comparable_columns].dropna(subset=effective_grouping_columns)
            grouped_counts = comparable_frame.groupby(effective_grouping_columns, dropna=False)[expectation.expected_period_column].nunique()
            comparable_groups = int((grouped_counts >= 2).sum())
            total_groups = int(len(grouped_counts))
            if comparable_groups == 0:
                return "invalid", "The grouped comparison did not return any groups with comparable periods."
            if comparable_groups < total_groups:
                return "partial", f"Only {comparable_groups} of {total_groups} groups returned comparable periods."

    if len(frame) < expectation.min_expected_rows:
        return "invalid", f"The step returned {len(frame)} rows, below the expected minimum of {expectation.min_expected_rows}."

    return "valid", None


def preflight_compiled_plan(state: AnalysisState, compiled_plan: dict[str, Any]) -> dict[str, Any]:
    """
    Validate compiled SQL steps against the active runtime before execution.

    Steps are checked in order so later queries can reference earlier output aliases.
    """

    conn = new_duckdb_connection()
    _register_artifacts(conn, state)
    rows = list(compiled_plan.get("plan") or [])
    rows.sort(key=lambda r: r["id"] if isinstance(r, dict) else r.id)
    previews: list[dict[str, Any]] = []

    for row in rows:
        internal = compiled_plan_row_to_internal(row)
        sql = internal["code"].strip().rstrip(";")
        try:
            preview = conn.execute(f"SELECT * FROM ({sql}) AS __planera_preflight LIMIT 0").fetchdf()
            preview_columns = list(preview.columns)
            validation_reason = _validate_preview_shape(internal, preview_columns)
            if validation_reason:
                return {
                    "status": "failed",
                    "failed_step_id": internal["id"],
                    "error": validation_reason,
                    "query": internal["code"],
                    "step_previews": previews,
                }
            previews.append(
                {
                    "step_id": internal["id"],
                    "columns": preview_columns,
                    "validation_status": "valid",
                }
            )
            conn.register(internal["output_alias"], preview)
        except Exception as exc:
            return {
                "status": "failed",
                "failed_step_id": internal["id"],
                "error": str(exc),
                "query": internal["code"],
                "step_previews": previews,
            }

    return {"status": "success", "step_previews": previews}


def _try_sql_step(
    state: AnalysisState,
    internal: dict[str, Any],
    attempt: int,
) -> tuple[Literal["success", "invalid", "failed"], ExecutedStep]:
    """Run one SQL step with semantic/result-shape validation."""

    state["total_steps"] += 1
    try:
        frame = _execute_sql(state, internal)
        artifact = _summarize_artifact(internal["output_alias"], frame)
        validation_status, validation_reason = _validate_result_shape(frame, internal)
        if validation_status == "invalid":
            state["artifacts"].pop(internal["output_alias"], None)
            executed = ExecutedStep(
                id=internal["id"],
                kind="sql",
                purpose=internal["purpose"],
                code=internal["code"],
                output_alias=internal["output_alias"],
                attempt=attempt,
                status="invalid",
                validation_status="invalid",
                validation_reason=validation_reason,
                expectation=_as_expectation(internal["expectation"]),
                error=validation_reason,
            )
            state["executed_steps"].append(executed.model_dump())
            state["last_error"] = {
                "step_id": internal["id"],
                "message": validation_reason,
                "code": internal["code"],
                "kind": "invalid",
            }
            return "invalid", executed

        state["artifacts"][internal["output_alias"]] = frame
        executed = ExecutedStep(
            id=internal["id"],
            kind="sql",
            purpose=internal["purpose"],
            code=internal["code"],
            output_alias=internal["output_alias"],
            attempt=attempt,
            status="success",
            validation_status=validation_status,
            validation_reason=validation_reason,
            expectation=_as_expectation(internal["expectation"]),
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
            validation_status="invalid",
            expectation=_as_expectation(internal["expectation"]),
            error=str(exc),
        )
        state["executed_steps"].append(executed.model_dump())
        state["last_error"] = {
            "step_id": internal["id"],
            "message": str(exc),
            "code": internal["code"],
            "kind": "failed",
        }
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
        if status in {"failed", "invalid"}:
            sid = internal["id"]
            return {
                "status": status,
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
    if status in {"failed", "invalid"}:
        return {
            "status": status,
            "failed_step_id": internal["id"],
            "error": state["last_error"]["message"] if state["last_error"] else "Unknown error",
        }
    return {"status": "success"}
