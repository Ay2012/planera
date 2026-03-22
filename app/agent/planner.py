"""Gemini-driven next-step planner."""

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

    prompt = f"""
You are the planning brain of a GTM analytics agent.

Your job is to choose the next exact executable step for answering the user query over the provided CRM sales dataset.

Rules:
- Metric scope is pipeline_velocity only.
- Return JSON only.
- You may choose exactly one action:
  1. "execute_step" with one SQL or pandas step
  2. "finish" if the evidence is sufficient for final verification and answer generation
- Prefer SQL against curated views whenever possible.
- Use only these views: {json.dumps([view["name"] for view in state["dataset_context"].get("views", [])])}
- For pandas steps, write code that assigns the final object to a variable named `result`.
- Never use imports, file I/O, network calls, or plotting.
- Keep each step small and purposeful.
- If the previous step failed, fix the cause directly instead of repeating the same broken query.
- Use categorical values exactly as shown in dataset_context. Status values are lowercase.
- Treat an empty result set as a failed step that must be corrected quickly.
- Aim to finish in at most 2 successful execution steps unless a prior step failed.

User query:
{state["query"]}

Dataset context:
{json.dumps(state["dataset_context"], indent=2)}

Completed steps:
{json.dumps(completed_steps, indent=2)}

Latest error:
{json.dumps(state["last_error"], indent=2) if state["last_error"] else "null"}

Return JSON in this shape:
{{
  "intent": "diagnosis|comparison|recommendation",
  "metric": "pipeline_velocity",
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
    """Call Gemini to produce the next step decision."""

    decision = get_llm_client().generate_json(_build_planner_prompt(state))
    parsed = PlannerDecision.model_validate(decision)

    state["intent"] = parsed.intent
    state["metric"] = parsed.metric
    state["planner_reasoning"] = parsed.reasoning_summary
    state["planner_action"] = parsed.action
    state["current_step"] = parsed.step.model_dump() if parsed.step else None
    state["loop_status"] = "ready_to_execute" if parsed.action == "execute_step" else "ready_to_verify"
    return state
