"""Step review and loop routing helpers."""

from __future__ import annotations

from app.agent.state import AnalysisState


def review_last_step(state: AnalysisState) -> AnalysisState:
    """Update retry and loop state after a step execution attempt."""

    if not state["executed_steps"]:
        state["loop_status"] = "planning"
        return state

    last_step = state["executed_steps"][-1]
    if last_step["status"] == "success":
        current_step = state.get("current_step") or {}
        artifact = last_step.get("artifact") or {}
        expected_output = current_step.get("expected_output", {})
        expected_columns = set(expected_output.get("columns", []))
        actual_columns = set(artifact.get("columns", []))

        empty_table = artifact.get("artifact_type") == "table" and artifact.get("row_count", 0) == 0
        missing_columns = bool(expected_columns and not expected_columns.issubset(actual_columns))

        if empty_table or missing_columns:
            message = "Step returned an empty result set." if empty_table else "Step output did not match expected columns."
            last_step["status"] = "failed"
            last_step["error"] = message
            state["last_error"] = {
                "step_id": last_step["id"],
                "message": message,
                "code": last_step["code"],
            }
            state["retry_count"] += 1
            state["loop_status"] = "fatal_error" if state["retry_count"] > state["max_retries"] else "planning"
            return state

        state["retry_count"] = 0
        if state["total_steps"] >= state["max_steps"]:
            state["loop_status"] = "ready_to_verify"
        else:
            state["loop_status"] = "planning"
        return state

    state["retry_count"] += 1
    if state["retry_count"] > state["max_retries"] or state["total_steps"] >= state["max_steps"]:
        state["loop_status"] = "fatal_error"
    else:
        state["loop_status"] = "planning"
    return state
