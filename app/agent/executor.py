"""Executor runtime for step-by-step SQL execution."""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.schemas import ArtifactSummary, ExecutedStep, StepFailureRecord
from app.data.semantic_model import new_duckdb_connection


def _summarize_artifact(alias: str, frame: pd.DataFrame) -> ArtifactSummary:
    preview_rows = frame.head(5).where(pd.notnull(frame), None).to_dict(orient="records")
    return ArtifactSummary(
        alias=alias,
        artifact_type="table",
        row_count=int(len(frame)),
        columns=list(frame.columns),
        preview_rows=preview_rows,
        summary={},
    )


def _register_stored_outputs(conn, state: dict[str, Any]) -> None:  # noqa: ANN001
    for alias, value in (state.get("stored_outputs") or {}).items():
        if isinstance(value, pd.DataFrame):
            conn.register(alias, value)


def _current_step(state: dict[str, Any]) -> dict[str, Any]:
    plan = state.get("current_plan") or {}
    steps = list(plan.get("steps") or [])
    step_index = int(state.get("current_step_index", 0) or 0)
    if step_index < 0 or step_index >= len(steps):
        raise ValueError(f"Current step index {step_index} is out of range for the active plan.")
    return steps[step_index]


def _record_failure(state: dict[str, Any], *, step: dict[str, Any], attempt: int, error: str, sql: str) -> None:
    failure = StepFailureRecord(
        step_id=int(step["id"]),
        attempt=attempt,
        error=error,
        query=sql,
        details={"output_alias": step["output_alias"]},
    )
    state.setdefault("failure_history", {}).setdefault(str(step["id"]), []).append(failure.model_dump())


def _record_error(
    state: dict[str, Any],
    *,
    step_name: str,
    message: str,
    recoverable: bool,
    details: dict[str, Any],
) -> None:
    state.setdefault("errors", []).append(
        {
            "step": step_name,
            "message": message,
            "recoverable": recoverable,
            "details": details,
        }
    )


def _failure_summary(step: dict[str, Any], error: str) -> str:
    relations = ", ".join(step.get("relations") or []) or "the active relations"
    return f"Execution repeatedly failed for step {step['id']} against {relations}: {error}"


def execute_current_step(state: dict[str, Any]) -> dict[str, Any]:
    """Execute the query for the current workflow step."""

    step = _current_step(state)
    generated_query = state.get("generated_query") or {}
    sql = str(generated_query.get("sql") or "").strip()
    if not sql:
        raise ValueError("No generated SQL is available for the current step.")

    attempt = int((state.get("retry_counts") or {}).get(str(step["id"]), 0) or 0) + 1
    conn = new_duckdb_connection(state.get("dataset_context"))
    try:
        _register_stored_outputs(conn, state)
        frame = conn.execute(sql).fetchdf()
    except Exception as exc:
        message = str(exc)
        executed = ExecutedStep(
            id=str(step["id"]),
            kind="sql",
            purpose=step["purpose"],
            code=sql,
            output_alias=step["output_alias"],
            attempt=attempt,
            status="failed",
            error=message,
        )
        state.setdefault("executed_steps", []).append(executed.model_dump())
        _record_failure(state, step=step, attempt=attempt, error=message, sql=sql)

        prior_retries = int((state.get("retry_counts") or {}).get(str(step["id"]), 0) or 0)
        if prior_retries < 1:
            state.setdefault("retry_counts", {})[str(step["id"])] = prior_retries + 1
            _record_error(
                state,
                step_name="executor_node",
                message=message,
                recoverable=True,
                details={"step_id": step["id"], "attempt": attempt},
            )
            state["workflow_status"] = "retry_same_step"
        elif int(state.get("replan_count", 0) or 0) < 1:
            state["failure_summary"] = _failure_summary(step, message)
            _record_error(
                state,
                step_name="executor_node",
                message=message,
                recoverable=True,
                details={"step_id": step["id"], "attempt": attempt, "action": "replan"},
            )
            state["workflow_status"] = "needs_replan"
        else:
            state["failure_summary"] = _failure_summary(step, message)
            _record_error(
                state,
                step_name="executor_node",
                message=message,
                recoverable=False,
                details={"step_id": step["id"], "attempt": attempt, "action": "best_effort"},
            )
            state["workflow_status"] = "best_effort"

        state["generated_query"] = None
        return state
    finally:
        conn.close()

    artifact = _summarize_artifact(step["output_alias"], frame)
    if artifact.row_count == 0 and not bool(step.get("allow_empty_result", False)):
        message = "Step returned an empty result set."
        executed = ExecutedStep(
            id=str(step["id"]),
            kind="sql",
            purpose=step["purpose"],
            code=sql,
            output_alias=step["output_alias"],
            attempt=attempt,
            status="failed",
            error=message,
        )
        state.setdefault("executed_steps", []).append(executed.model_dump())
        _record_failure(state, step=step, attempt=attempt, error=message, sql=sql)

        prior_retries = int((state.get("retry_counts") or {}).get(str(step["id"]), 0) or 0)
        if prior_retries < 1:
            state.setdefault("retry_counts", {})[str(step["id"])] = prior_retries + 1
            _record_error(
                state,
                step_name="executor_node",
                message=message,
                recoverable=True,
                details={"step_id": step["id"], "attempt": attempt},
            )
            state["workflow_status"] = "retry_same_step"
        elif int(state.get("replan_count", 0) or 0) < 1:
            state["failure_summary"] = _failure_summary(step, message)
            _record_error(
                state,
                step_name="executor_node",
                message=message,
                recoverable=True,
                details={"step_id": step["id"], "attempt": attempt, "action": "replan"},
            )
            state["workflow_status"] = "needs_replan"
        else:
            state["failure_summary"] = _failure_summary(step, message)
            _record_error(
                state,
                step_name="executor_node",
                message=message,
                recoverable=False,
                details={"step_id": step["id"], "attempt": attempt, "action": "best_effort"},
            )
            state["workflow_status"] = "best_effort"

        state["generated_query"] = None
        return state

    state.setdefault("stored_outputs", {})[step["output_alias"]] = frame
    executed = ExecutedStep(
        id=str(step["id"]),
        kind="sql",
        purpose=step["purpose"],
        code=sql,
        output_alias=step["output_alias"],
        attempt=attempt,
        status="success",
        artifact=artifact,
    )
    state.setdefault("executed_steps", []).append(executed.model_dump())
    state["generated_query"] = None

    plan = state.get("current_plan") or {}
    steps = list(plan.get("steps") or [])
    step_index = int(state.get("current_step_index", 0) or 0)
    if step_index + 1 < len(steps):
        state["current_step_index"] = step_index + 1
        state["workflow_status"] = "plan_ready"
    else:
        state["workflow_status"] = "ready_for_analysis"
    return state


def build_best_effort_state(state: dict[str, Any]) -> dict[str, Any]:
    """Populate the best-effort answer path after retry limits are exhausted."""

    successful_steps = [step for step in state.get("executed_steps") or [] if step.get("status") == "success"]
    answered_parts: list[str] = []
    if successful_steps:
        last_success = successful_steps[-1]
        artifact = last_success.get("artifact") or {}
        answered_parts.append(
            f"Captured {artifact.get('row_count', 0)} row(s) in {artifact.get('alias', last_success.get('output_alias', 'the final output'))}."
        )

    unanswered = state.get("failure_summary") or "The workflow could not complete every planned step."
    lines = [
        "## Best-effort answer",
        "",
        "Answered parts:",
        *(f"- {item}" for item in answered_parts or ["- No completed step produced a reusable final output."]),
        "",
        "Could not answer completely:",
        f"- {unanswered}",
    ]
    state["final_answer"] = "\n".join(lines).strip()
    state["analysis"] = state["final_answer"]
    state["workflow_status"] = "best_effort_ready"
    return state
