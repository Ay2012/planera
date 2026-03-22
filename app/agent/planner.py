"""LLM-driven compiled multi-step planner and repair."""

from __future__ import annotations

import json

from pydantic import ValidationError

from app.agent.state import AnalysisState
from app.llm import get_llm_client
from app.schemas import CompiledPlan, RepairDecision
from app.utils.logging import get_logger

logger = get_logger(__name__)

_COMPILED_PLANNER_ATTEMPTS = 3


def _build_compiled_planner_prompt(state: AnalysisState, validation_feedback: str | None = None) -> str:
    view_names = [view["name"] for view in state["dataset_context"].get("views", [])]

    prompt = f"""
You are the planning component of a GTM analytics agent.

Return a single JSON object that describes a full multi-step plan to answer the user's question using only the dataset described below.

Rules:
- Return JSON only.
- Produce 1 to 3 items in "plan" (at most three SQL steps). Each step must add incremental explanatory value; avoid redundant segmentation.
- CRITICAL — the "max_steps" field: set it to the integer 3 always. It is the platform's fixed ceiling, not the count of steps you return. Do not set max_steps to 1 or 2 even if the plan has only one or two queries.
- Every step must use "type": "sql" and put the full SQL statement in "query".
- Use only these registered view/table names: {json.dumps(view_names)}
- Prefer SQL over multiple trivial splits; combine logic when one query suffices.
- No imports, file I/O, network calls, or plotting.
- Optional "output_alias" per step for stable names; if omitted, the executor uses `step_<id>`.

Return JSON in this exact shape:
{{
  "objective": "string — what the plan will establish end-to-end",
  "plan": [
    {{
      "id": 1,
      "purpose": "string",
      "type": "sql",
      "query": "SQL query string"
    }}
  ],
  "max_steps": 3,
  "metric": "optional short label for the primary metric, or empty string",
  "metric_direction": "optional: e.g. higher_is_better or lower_is_better, or empty string"
}}

User query:
{state["query"]}

Dataset schema (tables, columns, dtypes, row counts):
{json.dumps(state["dataset_context"], indent=2)}
"""
    if validation_feedback:
        prompt += f"""

Your previous JSON was rejected by validation. Fix the structure and try again.
Validation errors:
{validation_feedback}
"""
    return prompt.strip()


def _build_repair_prompt(state: AnalysisState, failed_step_id: str, error_message: str) -> str:
    plan = state.get("compiled_plan") or {}
    prompt = f"""
You are the planning component of a GTM analytics agent. A SQL step from an existing plan failed execution.

Repair the failed step only: return JSON that replaces that step with corrected SQL. Do not add new steps.

Rules:
- Return JSON only.
- repair_action must be "replace_step".
- updated_step must use "type": "sql", the same id as the failed step ({failed_step_id}), and a fixed "query".
- Use only registered view names from the schema manifest.

Original plan:
{json.dumps(plan, indent=2)}

Failed step id: {failed_step_id}

Error message:
{error_message}

Schema manifest:
{json.dumps(state["dataset_context"], indent=2)}

Return JSON in this shape:
{{
  "repair_action": "replace_step",
  "updated_step": {{
    "id": <same int as failed step>,
    "purpose": "string",
    "type": "sql",
    "query": "corrected SQL"
  }}
}}
"""
    return prompt.strip()


def plan_compiled_query(state: AnalysisState) -> AnalysisState:
    """Call the LLM to produce a full compiled plan (max 3 SQL steps), with retries on schema errors."""

    client = get_llm_client()
    feedback: str | None = None

    for attempt in range(1, _COMPILED_PLANNER_ATTEMPTS + 1):
        prompt = _build_compiled_planner_prompt(state, validation_feedback=feedback)
        decision = client.generate_json(prompt)
        try:
            parsed = CompiledPlan.model_validate(decision)
        except ValidationError as exc:
            feedback = exc.json(indent=2)
            logger.warning(
                "Compiled plan validation failed (attempt %s/%s): %s",
                attempt,
                _COMPILED_PLANNER_ATTEMPTS,
                exc.errors(),
            )
            if attempt >= _COMPILED_PLANNER_ATTEMPTS:
                raise
            continue

        state["compiled_plan"] = parsed.model_dump()
        state["planner_reasoning"] = parsed.objective
        state["metric"] = parsed.metric
        state["intent"] = "diagnosis"
        state["workflow_status"] = "ready_to_execute"
        return state


def repair_failed_step(state: AnalysisState, failed_step_id: str, error_message: str) -> AnalysisState:
    """Call the LLM once to replace a single failed plan step."""

    raw = get_llm_client().generate_json(_build_repair_prompt(state, failed_step_id, error_message))
    parsed = RepairDecision.model_validate(raw)

    if str(parsed.updated_step.id) != str(failed_step_id):
        raise ValueError(f"Repair returned mismatched step id: expected {failed_step_id}, got {parsed.updated_step.id}")

    plan = state.get("compiled_plan")
    if not plan:
        raise ValueError("No compiled plan to repair.")

    steps = list(plan.get("plan") or [])
    replaced = False
    for i, row in enumerate(steps):
        sid = row.get("id") if isinstance(row, dict) else row["id"]
        if str(sid) == str(failed_step_id):
            steps[i] = parsed.updated_step.model_dump()
            replaced = True
            break
    if not replaced:
        raise ValueError(f"Failed step id {failed_step_id} not found in compiled plan.")

    plan["plan"] = steps
    state["compiled_plan"] = plan
    state["repair_attempted"] = True
    return state
