"""Single LLM pass: interpret executed results into an analytics narrative."""

from __future__ import annotations

import json

from app.agent.analysis_grounding import build_analysis_evidence, build_approved_claims, validate_rendered_analysis
from app.agent.state import AnalysisState
from app.llm import get_llm_client
from app.prompts import render_prompt
from app.schemas import AnalysisRenderResponse

_ANALYSIS_RENDER_ATTEMPTS = 2


def _build_analysis_render_prompt(
    question: str,
    approved_claims_json: str,
    validation_feedback: str | None = None,
) -> str:
    return render_prompt(
        "analysis_render.j2",
        question=question,
        approved_claims_json=approved_claims_json,
        validation_feedback=validation_feedback,
    )


def run_analysis_narrative(state: AnalysisState) -> AnalysisState:
    """Produce markdown-friendly analysis from query, objective, and step outputs."""

    workflow = state.get("workflow_status", "")
    if workflow in ("planner_failed", "execution_failed"):
        state["analysis"] = "The available evidence is insufficient because the workflow did not complete successfully."
        return state

    evidence = build_analysis_evidence(state)
    approved_claims, expected_status = build_approved_claims(evidence)
    if not approved_claims:
        state["analysis"] = "The approved claims are insufficient to answer the question with the available evidence."
        return state

    approved_claims_json = json.dumps([claim.model_dump() for claim in approved_claims], indent=2)
    feedback: str | None = None

    try:
        for attempt in range(1, _ANALYSIS_RENDER_ATTEMPTS + 1):
            prompt = _build_analysis_render_prompt(state["query"], approved_claims_json, validation_feedback=feedback)
            result = get_llm_client().generate_json(prompt, schema=AnalysisRenderResponse)
            parsed = result if isinstance(result, AnalysisRenderResponse) else AnalysisRenderResponse.model_validate(result)
            try:
                validate_rendered_analysis(parsed, approved_claims, expected_status)
            except ValueError as exc:
                feedback = str(exc)
                if attempt >= _ANALYSIS_RENDER_ATTEMPTS:
                    raise
                continue

            state["analysis"] = parsed.analysis_markdown.strip() or "No analysis text was returned."
            return state
    except Exception as exc:  # pragma: no cover - defensive
        state["analysis"] = (
            f"The analysis step could not complete ({exc!s}). "
            "Review the executed steps and trace for raw outputs."
        )
    return state
