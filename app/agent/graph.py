"""LangGraph workflow: schema context, compiled plan, deterministic execution, analysis."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agent.analysis import run_analysis_narrative
from app.agent.executor import execute_plan, execute_single_plan_step
from app.agent.planner import plan_compiled_query, repair_failed_step
from app.agent.state import AnalysisState, create_initial_state
from app.data.semantic_model import get_semantic_context
from app.utils.logging import get_logger

logger = get_logger(__name__)


def _append_trace(state: AnalysisState, step: str, status: str, details: dict[str, Any] | None = None) -> None:
    state["trace"].append({"step": step, "status": status, "details": details or {}})


def _append_error(state: AnalysisState, step: str, message: str, recoverable: bool = True, details: dict[str, Any] | None = None) -> None:
    state["errors"].append({"step": step, "message": message, "recoverable": recoverable, "details": details or {}})


def _has_usable_evidence(state: AnalysisState) -> bool:
    return any(
        step.get("status") == "success" and step.get("validation_status") in (None, "valid", "partial")
        for step in state.get("executed_steps") or []
    )


def load_schema_context_node(state: AnalysisState) -> AnalysisState:
    step_name = "load_schema_context_node"
    _append_trace(state, step_name, "started", {})
    context = get_semantic_context()
    state["dataset_context"] = context.schema_manifest
    _append_trace(
        state,
        step_name,
        "completed",
        {"reference_date": context.reference_date, "views": [v["name"] for v in context.schema_manifest.get("views", [])]},
    )
    return state


def planner_compiled_node(state: AnalysisState) -> AnalysisState:
    step_name = "planner_compiled_node"
    _append_trace(state, step_name, "started", {"total_steps": state["total_steps"]})
    try:
        state = plan_compiled_query(state)
        plan = state.get("compiled_plan") or {}
        _append_trace(
            state,
            step_name,
            "completed",
            {
                "objective": plan.get("objective"),
                "step_count": len(plan.get("plan") or []),
                "metric": plan.get("metric"),
            },
        )
    except Exception as exc:
        logger.warning("%s failed: %s", step_name, exc, exc_info=True)
        _append_error(state, step_name, str(exc), recoverable=False)
        state["workflow_status"] = "planner_failed"
        state["compiled_plan"] = None
        _append_trace(state, step_name, "failed", {"message": str(exc)})
    return state


def execute_plan_node(state: AnalysisState) -> AnalysisState:
    step_name = "execute_plan_node"
    if state["workflow_status"] == "planner_failed" or not state.get("compiled_plan"):
        _append_trace(state, step_name, "skipped", {"reason": "no compiled plan"})
        return state

    plan = state["compiled_plan"]
    if not plan.get("plan"):
        msg = "Planner returned an empty plan."
        _append_error(state, step_name, msg, recoverable=False)
        state["workflow_status"] = "execution_failed"
        _append_trace(state, step_name, "failed", {"message": msg})
        return state

    _append_trace(state, step_name, "started", {"steps": len(plan["plan"])})
    outcome = execute_plan(state, plan)

    if outcome["status"] == "success":
        state["workflow_status"] = "ready_to_analyze"
        state["unresolved_step_ids"] = []
        _append_trace(state, step_name, "completed", {"status": "success"})
        return state

    failed_id = outcome["failed_step_id"]
    err = outcome.get("error", "Unknown execution error")

    try:
        state = repair_failed_step(state, failed_id, err)
    except Exception as exc:
        _append_error(state, "repair_planner", str(exc), recoverable=False, details={"failed_step_id": failed_id})
        state["unresolved_step_ids"] = [failed_id]
        state["workflow_status"] = "partial_execution" if _has_usable_evidence(state) else "execution_failed"
        _append_trace(state, step_name, "failed", {"phase": "repair", "message": str(exc)})
        return state

    if state["executed_steps"] and state["executed_steps"][-1]["status"] in {"failed", "invalid"}:
        state["executed_steps"].pop()

    plan = state["compiled_plan"] or {}
    step_row = next((r for r in (plan.get("plan") or []) if str(r.get("id")) == str(failed_id)), None)
    if not step_row:
        _append_error(state, step_name, "Repaired step missing from plan.", recoverable=False)
        state["workflow_status"] = "execution_failed"
        return state

    retry = execute_single_plan_step(state, step_row, attempt=2)
    if retry["status"] in {"failed", "invalid"}:
        _append_error(
            state,
            step_name,
            f"Step {retry.get('failed_step_id', failed_id)} failed after repair: {retry.get('error', err)}",
            recoverable=False,
            details={"failed_step_id": failed_id},
        )
        state["unresolved_step_ids"] = [failed_id]
        state["workflow_status"] = "partial_execution" if _has_usable_evidence(state) else "execution_failed"
        _append_trace(state, step_name, "failed", {"phase": "retry", "failed_step_id": failed_id})
    else:
        state["workflow_status"] = "ready_to_analyze"
        state["unresolved_step_ids"] = []
        _append_trace(state, step_name, "completed", {"status": "success_after_repair"})

    return state


def analysis_node(state: AnalysisState) -> AnalysisState:
    step_name = "analysis_node"
    _append_trace(state, step_name, "started", {"workflow_status": state["workflow_status"]})
    try:
        state = run_analysis_narrative(state)
        _append_trace(state, step_name, "completed", {"length": len(state["analysis"])})
    except Exception as exc:
        logger.warning("%s failed: %s", step_name, exc, exc_info=True)
        state["analysis"] = "The available evidence is incomplete for a full answer."
        state["answer_status"] = "partial_answer" if _has_usable_evidence(state) else "insufficient_evidence"
        _append_error(
            state,
            step_name,
            "The workflow could not render a fully validated narrative for this run.",
            recoverable=False,
        )
        _append_trace(
            state,
            step_name,
            "failed",
            {"message": "The workflow could not render a fully validated narrative for this run."},
        )
    return state


def route_after_planner(state: AnalysisState) -> str:
    if state["workflow_status"] == "planner_failed":
        return "analysis_node"
    return "execute_plan_node"


@lru_cache(maxsize=1)
def build_graph():
    """Compile and cache the LangGraph workflow."""

    graph = StateGraph(AnalysisState)
    graph.add_node("load_schema_context_node", load_schema_context_node)
    graph.add_node("planner_compiled_node", planner_compiled_node)
    graph.add_node("execute_plan_node", execute_plan_node)
    graph.add_node("analysis_node", analysis_node)

    graph.add_edge(START, "load_schema_context_node")
    graph.add_edge("load_schema_context_node", "planner_compiled_node")
    graph.add_conditional_edges("planner_compiled_node", route_after_planner)
    graph.add_edge("execute_plan_node", "analysis_node")
    graph.add_edge("analysis_node", END)
    return graph.compile()


def run_analysis(query: str) -> AnalysisState:
    """Execute the full workflow for a single user query."""

    workflow = build_graph()
    return workflow.invoke(create_initial_state(query))
