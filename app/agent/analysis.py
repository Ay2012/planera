"""Final analyzer runtime for the schema-grounded workflow."""

from __future__ import annotations

import json
from typing import Any

from app.llm import get_llm_client
from app.prompts import render_prompt
from app.schemas import AnalyzerDecision


def _fallback_best_effort_answer(state: dict[str, Any]) -> str:
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
    return "\n".join(lines).strip()


def _fallback_final_answer(state: dict[str, Any]) -> AnalyzerDecision:
    plan = state.get("current_plan") or {}
    unsupported = plan.get("unsupported_requirements") or []
    successful_steps = [step for step in state.get("executed_steps") or [] if step.get("status") == "success"]

    if state.get("workflow_status") == "best_effort_ready":
        return AnalyzerDecision(
            decision="final_answer",
            summary="Returning the bounded best-effort answer.",
            key_findings=[],
            important_metrics=[],
            caveats=[state.get("failure_summary", "")] if state.get("failure_summary") else [],
            final_answer=state.get("final_answer") or _fallback_best_effort_answer(state),
            failure_summary="",
        )

    if unsupported and not successful_steps:
        caveats = [item.get("description", "") for item in unsupported if item.get("description")]
        final_answer = "\n".join(
            [
                "## Summary",
                "The available uploaded schema/context does not fully support this question.",
                *(f"- {item}" for item in caveats),
            ]
        ).strip()
        return AnalyzerDecision(
            decision="final_answer",
            summary="The available schema/context does not fully support the request.",
            key_findings=[],
            important_metrics=[],
            caveats=caveats,
            final_answer=final_answer,
            failure_summary="",
        )

    if successful_steps:
        last_success = successful_steps[-1]
        artifact = last_success.get("artifact") or {}
        return AnalyzerDecision(
            decision="final_answer",
            summary="The workflow produced a final output ready for review.",
            key_findings=[f"{artifact.get('row_count', 0)} row(s) returned by the final step."],
            important_metrics=[],
            caveats=[state.get("failure_summary", "")] if state.get("failure_summary") else [],
            final_answer="\n".join(
                [
                    "## Summary",
                    f"The final output alias is {artifact.get('alias', last_success.get('output_alias', 'final_output'))}.",
                    f"{artifact.get('row_count', 0)} row(s) were returned by the final executed step.",
                ]
            ).strip(),
            failure_summary="",
        )

    if int(state.get("replan_count", 0) or 0) < 1 and state.get("failure_summary"):
        return AnalyzerDecision(
            decision="replan",
            summary="The collected outputs are not sufficient yet.",
            key_findings=[],
            important_metrics=[],
            caveats=[],
            final_answer="",
            failure_summary=state["failure_summary"],
        )

    best_effort = _fallback_best_effort_answer(state)
    return AnalyzerDecision(
        decision="final_answer",
        summary="Returning the best-effort answer after bounded retries.",
        key_findings=[],
        important_metrics=[],
        caveats=[state.get("failure_summary", "")] if state.get("failure_summary") else [],
        final_answer=best_effort,
        failure_summary="",
    )


def _build_analyzer_prompt(state: dict[str, Any]) -> str:
    plan = state.get("current_plan") or {}
    payload = {
        "question": state["query"],
        "workflow_status": state.get("workflow_status", ""),
        "replan_count": state.get("replan_count", 0),
        "failure_summary": state.get("failure_summary", ""),
        "schema_context_summary": state.get("schema_context_summary") or {},
        "plan": plan,
        "executed_steps": state.get("executed_steps") or [],
        "errors": state.get("errors") or [],
        "failure_history": state.get("failure_history") or {},
    }
    return render_prompt(
        "analysis_final.j2",
        analyzer_input_json=json.dumps(payload, indent=2, default=str),
    )


def analyze_workflow(state: dict[str, Any]) -> dict[str, Any]:
    """Produce the final analyzer decision for the workflow run."""

    try:
        result = get_llm_client().generate_json(_build_analyzer_prompt(state), schema=AnalyzerDecision)
        decision = result if isinstance(result, AnalyzerDecision) else AnalyzerDecision.model_validate(result)
    except Exception:
        decision = _fallback_final_answer(state)

    state["analyzer_result"] = decision.model_dump()
    if decision.decision == "replan" and int(state.get("replan_count", 0) or 0) < 1:
        state["workflow_status"] = "needs_replan"
        state["failure_summary"] = decision.failure_summary or state.get("failure_summary", "")
        return state

    final_answer = decision.final_answer or _fallback_final_answer(state).final_answer
    state["analysis"] = final_answer
    state["final_answer"] = final_answer
    state["workflow_status"] = "complete"
    return state


def run_analysis_narrative(state: dict[str, Any]) -> dict[str, Any]:
    """Compatibility wrapper retained for test and integration callers."""

    return analyze_workflow(state)


__all__ = ["analyze_workflow", "get_llm_client", "run_analysis_narrative"]
