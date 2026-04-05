"""Single LLM pass: interpret executed results into an analytics narrative."""

from __future__ import annotations

import json

from app.agent.analysis_grounding import build_analysis_evidence, build_approved_claims, validate_rendered_analysis
from app.agent.state import AnalysisState
from app.llm import get_llm_client
from app.prompts import render_prompt
from app.schemas import AnalysisRenderResponse, ApprovedClaim
from app.utils.logging import get_logger

_ANALYSIS_RENDER_ATTEMPTS = 2
logger = get_logger(__name__)


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


def _render_fallback_analysis(claims: list[ApprovedClaim], answer_status: str) -> str:
    substantive = [claim for claim in claims if claim.kind != "caveat"]
    caveats = [claim for claim in claims if claim.kind == "caveat"]

    if answer_status == "contradicted_premise" and substantive:
        lines = [substantive[0].statement]
        lines.extend(f"- {claim.statement}" for claim in substantive[1:3])
        if caveats:
            lines.append("")
            lines.append("Some requested breakdowns remain unresolved:")
            lines.extend(f"- {claim.statement}" for claim in caveats[:2])
        return "\n".join(lines)

    if answer_status == "partial_answer" and substantive:
        lines = ["The available evidence establishes part of the answer, but not the full requested breakdown."]
        lines.extend(f"- {claim.statement}" for claim in substantive[:3])
        if caveats:
            lines.append("")
            lines.append("Unresolved parts:")
            lines.extend(f"- {claim.statement}" for claim in caveats[:2])
        return "\n".join(lines)

    if answer_status == "conflicting_evidence":
        return "The available evidence is internally inconsistent, so Planera cannot validate a reliable conclusion."

    if substantive:
        lines = [substantive[0].statement]
        lines.extend(f"- {claim.statement}" for claim in substantive[1:3])
        return "\n".join(lines)

    if caveats:
        lines = [caveats[0].statement]
        if len(caveats) > 1:
            lines.extend(f"- {claim.statement}" for claim in caveats[1:3])
        return "\n".join(lines)

    return "The workflow could not validate a reliable comparison from the available results."


def run_analysis_narrative(state: AnalysisState) -> AnalysisState:
    """Produce markdown-friendly analysis from query, objective, and step outputs."""

    evidence = build_analysis_evidence(state)
    caveat_steps = [
        step
        for step in state.get("executed_steps") or []
        if step.get("status") in {"failed", "invalid"}
        or (step.get("status") == "success" and step.get("validation_status") == "partial")
    ]
    approved_claims, expected_status = build_approved_claims(evidence, unresolved_steps=caveat_steps)
    state["answer_status"] = expected_status
    if not approved_claims:
        state["analysis"] = _render_fallback_analysis([], expected_status)
        return state
    if all(claim.kind == "caveat" for claim in approved_claims):
        state["analysis"] = _render_fallback_analysis(approved_claims, expected_status)
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

            state["answer_status"] = parsed.answer_status
            state["analysis"] = parsed.analysis_markdown.strip() or "No analysis text was returned."
            return state
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Analysis rendering fell back to deterministic summary: %s", exc, exc_info=True)
        state["analysis"] = _render_fallback_analysis(approved_claims, expected_status)
    return state
