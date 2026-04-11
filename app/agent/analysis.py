"""Temporary analyzer runtime for the staged workflow implementation."""

from __future__ import annotations

from typing import Any

from app.schemas import AnalyzerDecision


def analyze_workflow(state: dict[str, Any]) -> dict[str, Any]:
    """Produce the final analyzer decision for the workflow run."""

    plan = state.get("current_plan") or {}
    successful_steps = [step for step in state.get("executed_steps") or [] if step.get("status") == "success"]
    unsupported = plan.get("unsupported_requirements") or []

    if state.get("workflow_status") == "best_effort_ready":
        final_answer = state.get("final_answer", "").strip()
        decision = AnalyzerDecision(
            decision="final_answer",
            summary="Returning the bounded best-effort answer.",
            key_findings=[],
            important_metrics=[],
            caveats=[state.get("failure_summary", "")] if state.get("failure_summary") else [],
            final_answer=final_answer,
            failure_summary="",
        )
        state["analyzer_result"] = decision.model_dump()
        state["analysis"] = final_answer
        state["workflow_status"] = "complete"
        return state

    if not plan.get("steps") and unsupported:
        caveats = [item.get("description", "") for item in unsupported if item.get("description")]
        final_answer = "\n".join(
            [
                "## Summary",
                "The available uploaded schema/context does not fully support this question.",
                *(f"- {item}" for item in caveats),
            ]
        ).strip()
        decision = AnalyzerDecision(
            decision="final_answer",
            summary="The planner found unsupported requirements before execution.",
            key_findings=[],
            important_metrics=[],
            caveats=caveats,
            final_answer=final_answer,
            failure_summary="",
        )
        state["analyzer_result"] = decision.model_dump()
        state["analysis"] = final_answer
        state["final_answer"] = final_answer
        state["workflow_status"] = "complete"
        return state

    if successful_steps:
        last_success = successful_steps[-1]
        artifact = last_success.get("artifact") or {}
        preview_rows = artifact.get("preview_rows") or []
        preview_line = ""
        if preview_rows:
            preview_line = f"Preview rows are available from {artifact.get('alias', last_success.get('output_alias', 'the final output'))}."
        final_answer = "\n".join(
            [
                "## Summary",
                f"The workflow completed {len(successful_steps)} successful step(s).",
                f"The final output alias is {artifact.get('alias', last_success.get('output_alias', 'final_output'))}.",
                preview_line,
            ]
        ).strip()
        decision = AnalyzerDecision(
            decision="final_answer",
            summary="The workflow produced a final output ready for review.",
            key_findings=[f"{artifact.get('row_count', 0)} row(s) returned by the final step."],
            important_metrics=[],
            caveats=[state.get("failure_summary", "")] if state.get("failure_summary") else [],
            final_answer=final_answer,
            failure_summary="",
        )
        state["analyzer_result"] = decision.model_dump()
        state["analysis"] = final_answer
        state["final_answer"] = final_answer
        state["workflow_status"] = "complete"
        return state

    if int(state.get("replan_count", 0) or 0) < 1 and state.get("failure_summary"):
        decision = AnalyzerDecision(
            decision="replan",
            summary="The collected outputs are not sufficient yet.",
            key_findings=[],
            important_metrics=[],
            caveats=[],
            final_answer="",
            failure_summary=state["failure_summary"],
        )
        state["analyzer_result"] = decision.model_dump()
        state["workflow_status"] = "needs_replan"
        return state

    fallback = state.get("failure_summary") or "The workflow could not produce a usable final output."
    final_answer = "\n".join(
        [
            "## Best-effort answer",
            "The workflow could not complete all planned steps.",
            f"- {fallback}",
        ]
    ).strip()
    decision = AnalyzerDecision(
        decision="final_answer",
        summary="Returning the best-effort answer after bounded retries.",
        key_findings=[],
        important_metrics=[],
        caveats=[fallback],
        final_answer=final_answer,
        failure_summary="",
    )
    state["analyzer_result"] = decision.model_dump()
    state["analysis"] = final_answer
    state["final_answer"] = final_answer
    state["workflow_status"] = "complete"
    return state


__all__ = ["analyze_workflow"]
