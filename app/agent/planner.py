"""LLM-driven next-step planner."""

from __future__ import annotations

import json

from app.agent.state import AnalysisState
from app.llm import get_llm_client
from app.schemas import PlannerDecision


def _build_planner_prompt(state: AnalysisState) -> str:
    completed_steps = [
        {
            "id": step["id"],
            "purpose": step["purpose"],
            "status": step["status"],
            "output_alias": step["output_alias"],
            "artifact_summary": step.get("artifact", {}),
            "error": step.get("error"),
        }
        for step in state["executed_steps"]
    ]
    view_names = [view["name"] for view in state["dataset_context"].get("views", [])]

    prompt = f"""
You are the planning component of a GTM analytics agent.

Choose the next executable step to answer the user's question using only the dataset described below.

Rules:
- Return JSON only.
- Choose exactly one action:
  1. "execute_step" — one SQL or pandas step
  2. "finish" — enough has been computed to hand off to the analysis step (no more code runs)
- Prefer SQL against the registered views when possible.
- Use only these views/tables: {json.dumps(view_names)}
- For pandas steps, assign the final result to a variable named `result`.
- No imports, file I/O, network calls, or plotting.
- Keep each step small. If the previous step failed, fix the cause instead of repeating the same mistake.
- Treat an empty result table as a failure to correct on the next iteration.
- Prefer to finish after a small number of successful steps unless errors forced extra attempts.

User query:
{state["query"]}

Dataset schema (tables, columns, dtypes, row counts):
{json.dumps(state["dataset_context"], indent=2)}

Completed steps:
{json.dumps(completed_steps, indent=2)}

Latest error:
{json.dumps(state["last_error"], indent=2) if state["last_error"] else "null"}

Return JSON in this shape:
{{
  "intent": "diagnosis|comparison|recommendation",
  "metric": "<short label for what you are measuring, or empty string>",
  "reasoning_summary": "...",
  "action": "execute_step|finish",
  "completion_reason": "optional when action is finish",
  "step": {{
    "id": "step_x",
    "kind": "sql|pandas",
    "purpose": "...",
    "input_views": ["..."],
    "code": "...",
    "output_alias": "...",
    "expected_output": {{"type": "table|scalar", "columns": ["..."]}},
    "success_criteria": ["..."],
    "is_final_step": false
  }}
}}
"""
    return prompt.strip()


def plan_next_step(state: AnalysisState) -> AnalysisState:
    """Call the LLM to produce the next step decision."""

    decision = get_llm_client().generate_json(_build_planner_prompt(state))
    parsed = PlannerDecision.model_validate(decision)

    state["intent"] = parsed.intent
    state["metric"] = parsed.metric
    state["planner_reasoning"] = parsed.reasoning_summary
    state["planner_action"] = parsed.action
    state["current_step"] = parsed.step.model_dump() if parsed.step else None
    state["loop_status"] = "ready_to_execute" if parsed.action == "execute_step" else "ready_to_analyze"
    return state
