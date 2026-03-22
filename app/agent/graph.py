"""LangGraph workflow: schema context, planner/execute/review loop, analysis."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agent.analysis import run_analysis_narrative
from app.agent.executor import execute_current_step
from app.agent.planner import plan_next_step
from app.agent.reviewer import review_last_step
from app.agent.state import AnalysisState, create_initial_state
from app.data.semantic_model import get_semantic_context


def _append_trace(state: AnalysisState, step: str, status: str, details: dict[str, Any] | None = None) -> None:
    state["trace"].append({"step": step, "status": status, "details": details or {}})


def _append_error(state: AnalysisState, step: str, message: str, recoverable: bool = True, details: dict[str, Any] | None = None) -> None:
    state["errors"].append({"step": step, "message": message, "recoverable": recoverable, "details": details or {}})


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


def planner_node(state: AnalysisState) -> AnalysisState:
    step_name = "planner_node"
    _append_trace(state, step_name, "started", {"retry_count": state["retry_count"], "total_steps": state["total_steps"]})
    try:
        state = plan_next_step(state)
        _append_trace(
            state,
            step_name,
            "completed",
            {"action": state["planner_action"], "reasoning": state["planner_reasoning"], "step": state["current_step"]},
        )
    except Exception as exc:
        _append_error(state, step_name, str(exc), recoverable=False)
        state["loop_status"] = "fatal_error"
        _append_trace(state, step_name, "failed", {"message": str(exc)})
    return state


def execution_node(state: AnalysisState) -> AnalysisState:
    step_name = "execution_node"
    _append_trace(state, step_name, "started", {"step": state["current_step"]})
    state = execute_current_step(state)
    last = state["executed_steps"][-1]
    if last["status"] == "failed":
        _append_error(state, step_name, last["error"] or "Unknown execution error", recoverable=True, details={"step_id": last["id"]})
        _append_trace(state, step_name, "failed", {"step_id": last["id"], "error": last["error"]})
    else:
        _append_trace(state, step_name, "completed", {"step_id": last["id"], "artifact": last["artifact"]})
    return state


def review_node(state: AnalysisState) -> AnalysisState:
    step_name = "review_node"
    _append_trace(state, step_name, "started", {"loop_status": state["loop_status"]})
    state = review_last_step(state)
    _append_trace(state, step_name, "completed", {"loop_status": state["loop_status"], "retry_count": state["retry_count"]})
    return state


def analysis_node(state: AnalysisState) -> AnalysisState:
    step_name = "analysis_node"
    _append_trace(state, step_name, "started", {})
    try:
        state = run_analysis_narrative(state)
        _append_trace(state, step_name, "completed", {"length": len(state["analysis"])})
    except Exception as exc:
        state["analysis"] = f"The analysis step failed: {exc}"
        _append_error(state, step_name, str(exc), recoverable=False)
        _append_trace(state, step_name, "failed", {"message": str(exc)})
    return state


def route_after_planner(state: AnalysisState) -> str:
    if state["loop_status"] == "fatal_error":
        return "analysis_node"
    if state["planner_action"] == "finish":
        return "analysis_node"
    return "execution_node"


def route_after_review(state: AnalysisState) -> str:
    if state["loop_status"] == "fatal_error":
        return "analysis_node"
    if state["loop_status"] == "ready_to_analyze":
        return "analysis_node"
    return "planner_node"


@lru_cache(maxsize=1)
def build_graph():
    """Compile and cache the LangGraph workflow."""

    graph = StateGraph(AnalysisState)
    graph.add_node("load_schema_context_node", load_schema_context_node)
    graph.add_node("planner_node", planner_node)
    graph.add_node("execution_node", execution_node)
    graph.add_node("review_node", review_node)
    graph.add_node("analysis_node", analysis_node)

    graph.add_edge(START, "load_schema_context_node")
    graph.add_edge("load_schema_context_node", "planner_node")
    graph.add_conditional_edges("planner_node", route_after_planner)
    graph.add_edge("execution_node", "review_node")
    graph.add_conditional_edges("review_node", route_after_review)
    graph.add_edge("analysis_node", END)
    return graph.compile()


def run_analysis(query: str) -> AnalysisState:
    """Execute the full workflow for a single user query."""

    workflow = build_graph()
    return workflow.invoke(create_initial_state(query))
