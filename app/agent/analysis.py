"""Single LLM pass: interpret executed results into an analytics narrative."""

from __future__ import annotations

import json

from app.agent.state import AnalysisState
from app.llm import get_llm_client
from app.schemas import AnalysisNarrativeResponse


def run_analysis_narrative(state: AnalysisState) -> AnalysisState:
    """Produce markdown-friendly analysis from query, objective, and step outputs."""

    plan = state.get("compiled_plan") or {}
    objective = plan.get("objective") or ""
    metric = plan.get("metric") or state.get("metric") or ""
    metric_direction = plan.get("metric_direction") or ""

    workflow = state.get("workflow_status", "")
    failure_note = ""
    if workflow in ("planner_failed", "execution_failed"):
        errs = state.get("errors") or []
        summary = "; ".join(e.get("message", "") for e in errs[-3:]) if errs else "See trace and errors."
        failure_note = f"\nWorkflow note: execution did not complete successfully ({workflow}). {summary}\n"

    prompt = f"""
You are a GTM analytics analyst. Explain what the data shows in response to the user's question.

Rules:
- Base conclusions only on the executed steps and their artifacts below. Do not invent numbers.
- If there were no successful steps or data is insufficient, say so clearly.
- Use markdown: short headings, bullets where helpful.
- Follow the response schema exactly. The content should match this shape:
{{ "analysis": "<markdown string>" }}

User question:
{state["query"]}

Analytical objective (from planner):
{objective}

Primary metric (if provided): {metric}
Metric directionality (if provided): {metric_direction}
{failure_note}
Dataset schema (reference):
{json.dumps(state["dataset_context"], indent=2)}

Executed steps (with previews where available):
{json.dumps(state["executed_steps"], indent=2)}
"""
    try:
        result = get_llm_client().generate_json(prompt, schema=AnalysisNarrativeResponse)
        parsed = result if isinstance(result, AnalysisNarrativeResponse) else AnalysisNarrativeResponse.model_validate(result)
        state["analysis"] = parsed.analysis.strip() or "No analysis text was returned."
    except Exception as exc:  # pragma: no cover - defensive
        state["analysis"] = (
            f"The analysis step could not complete ({exc!s}). "
            "Review the executed steps and trace for raw outputs."
        )
    return state
