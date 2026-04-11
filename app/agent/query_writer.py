"""Query-writer runtime for step-by-step SQL generation."""

from __future__ import annotations

import json
from typing import Any

from app.llm import get_llm_client
from app.prompts import render_prompt
from app.schemas import GeneratedQuery


def _get_current_step(state: dict[str, Any]) -> dict[str, Any]:
    plan = state.get("current_plan") or {}
    steps = list(plan.get("steps") or [])
    if not steps:
        raise ValueError("No planner-authored steps are available for query writing.")

    step_index = int(state.get("current_step_index", 0) or 0)
    if step_index < 0 or step_index >= len(steps):
        raise ValueError(f"Current step index {step_index} is out of range for the active plan.")
    return steps[step_index]


def _prior_output_summaries(state: dict[str, Any], current_step: dict[str, Any]) -> list[dict[str, Any]]:
    needed = {str(step_id) for step_id in current_step.get("depends_on") or []}
    if not needed:
        return []

    summaries: list[dict[str, Any]] = []
    for step in state.get("executed_steps") or []:
        if step.get("status") != "success":
            continue
        if str(step.get("id")) not in needed:
            continue
        artifact = step.get("artifact") or {}
        summaries.append(
            {
                "step_id": step.get("id"),
                "output_alias": step.get("output_alias"),
                "purpose": step.get("purpose"),
                "artifact": {
                    "alias": artifact.get("alias"),
                    "row_count": artifact.get("row_count", 0),
                    "columns": artifact.get("columns") or [],
                    "preview_rows": artifact.get("preview_rows") or [],
                },
            }
        )
    return summaries


def write_step_query(state: dict[str, Any]) -> dict[str, Any]:
    """Generate one SQL query for the current workflow step."""

    current_step = _get_current_step(state)
    prior_outputs = _prior_output_summaries(state, current_step)
    error_context = ""
    failures = state.get("failure_history", {}).get(str(current_step["id"]), [])
    if failures:
        error_context = failures[-1].get("error", "")

    prompt = render_prompt(
        "query_writer.j2",
        query=state["query"],
        step_json=json.dumps(current_step, indent=2),
        schema_context_json=json.dumps(state.get("schema_context_summary") or {}, indent=2),
        prior_outputs_json=json.dumps(prior_outputs, indent=2),
        error_context=error_context,
    )
    result = get_llm_client().generate_json(prompt, schema=GeneratedQuery)
    parsed = result if isinstance(result, GeneratedQuery) else GeneratedQuery.model_validate(result)
    state["generated_query"] = parsed.model_dump()
    state.setdefault("step_queries", {}).setdefault(str(current_step["id"]), []).append(parsed.sql)
    state["workflow_status"] = "query_ready"
    return state


__all__ = ["get_llm_client", "write_step_query"]
