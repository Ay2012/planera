"""LangGraph orchestration for the schema-grounded analytics workflow."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agent.analysis import analyze_workflow
from app.agent.executor import build_best_effort_state, execute_current_step
from app.agent.planner import plan_analysis, replan_analysis
from app.agent.query_writer import write_step_query
from app.agent.state import AnalysisState, create_initial_state
from app.data.semantic_model import get_semantic_context


def _append_trace(state: dict[str, Any], step: str, status: str, details: dict[str, Any] | None = None) -> None:
    state.setdefault("trace", []).append({"step": step, "status": status, "details": details or {}})


def _append_error(
    state: dict[str, Any],
    *,
    step: str,
    message: str,
    recoverable: bool,
    details: dict[str, Any] | None = None,
) -> None:
    state.setdefault("errors", []).append(
        {
            "step": step,
            "message": message,
            "recoverable": recoverable,
            "details": details or {},
        }
    )


def run_analysis(query: str, source_ids: list[str] | None = None) -> dict[str, Any]:
    """Compatibility entrypoint used by the API service layer."""

    workflow = build_graph()
    return workflow.invoke(create_initial_state(query, source_ids=source_ids))


def load_schema_context_node(state: dict[str, Any]) -> dict[str, Any]:
    """Load schema context into workflow state."""

    step_name = "load_schema_context_node"
    _append_trace(state, step_name, "started", {})
    context = get_semantic_context(state.get("source_ids"))
    state["dataset_context"] = context.schema_manifest
    _append_trace(
        state,
        step_name,
        "completed",
        {
            "reference_date": context.reference_date,
            "relations": [relation["name"] for relation in context.schema_manifest.get("relations", [])],
        },
    )
    state["workflow_status"] = "schema_ready"
    return state


def planner_node(state: dict[str, Any]) -> dict[str, Any]:
    """Create the full ordered plan for the request."""

    step_name = "planner_node"
    _append_trace(state, step_name, "started", {"replan_count": state.get("replan_count", 0)})
    try:
        state = plan_analysis(state)
    except Exception as exc:
        message = str(exc)
        _append_error(state, step=step_name, message=message, recoverable=False)
        _append_trace(state, step_name, "failed", {"message": message})
        state["failure_summary"] = message
        state["workflow_status"] = "best_effort"
        return state

    steps = list((state.get("current_plan") or {}).get("steps") or [])
    if steps:
        _append_trace(state, step_name, "completed", {"step_count": len(steps)})
        state["workflow_status"] = "plan_ready"
    else:
        _append_trace(state, step_name, "completed", {"step_count": 0})
        state["workflow_status"] = "ready_for_analysis"
    return state


def query_writer_node(state: dict[str, Any]) -> dict[str, Any]:
    """Generate exactly one query for the current step."""

    step_name = "query_writer_node"
    _append_trace(state, step_name, "started", {"current_step_index": state.get("current_step_index", 0)})
    try:
        state = write_step_query(state)
    except Exception as exc:
        message = str(exc)
        _append_error(state, step=step_name, message=message, recoverable=False)
        _append_trace(state, step_name, "failed", {"message": message})
        state["failure_summary"] = message
        state["workflow_status"] = "best_effort"
        return state

    generated_query = state.get("generated_query") or {}
    _append_trace(
        state,
        step_name,
        "completed",
        {"step_id": generated_query.get("step_id"), "query_length": len(generated_query.get("sql", ""))},
    )
    return state


def executor_node(state: dict[str, Any]) -> dict[str, Any]:
    """Execute the current step and store any successful output."""

    step_name = "executor_node"
    current_step_index = state.get("current_step_index", 0)
    _append_trace(state, step_name, "started", {"current_step_index": current_step_index})
    try:
        state = execute_current_step(state)
    except Exception as exc:
        message = str(exc)
        _append_error(state, step=step_name, message=message, recoverable=False)
        _append_trace(state, step_name, "failed", {"message": message})
        state["failure_summary"] = message
        state["workflow_status"] = "best_effort"
        return state

    _append_trace(state, step_name, "completed", {"workflow_status": state.get("workflow_status", "")})
    return state


def analyzer_node(state: dict[str, Any]) -> dict[str, Any]:
    """Produce the final answer or request a replan."""

    step_name = "analyzer_node"
    _append_trace(state, step_name, "started", {"workflow_status": state.get("workflow_status", "")})
    try:
        state = analyze_workflow(state)
    except Exception as exc:
        message = str(exc)
        _append_error(state, step=step_name, message=message, recoverable=False)
        _append_trace(state, step_name, "failed", {"message": message})
        state["failure_summary"] = message
        state["workflow_status"] = "best_effort"
        return state

    decision = (state.get("analyzer_result") or {}).get("decision", "")
    _append_trace(state, step_name, "completed", {"decision": decision})
    return state


def replan_node(state: dict[str, Any]) -> dict[str, Any]:
    """Request one bounded replan after analyzer or execution failure."""

    step_name = "replan_node"
    _append_trace(state, step_name, "started", {"failure_summary": state.get("failure_summary", "")})
    try:
        state = replan_analysis(state)
    except Exception as exc:
        message = str(exc)
        _append_error(state, step=step_name, message=message, recoverable=False)
        _append_trace(state, step_name, "failed", {"message": message})
        state["failure_summary"] = message
        state["workflow_status"] = "best_effort"
        return state

    state["current_step_index"] = 0
    state["generated_query"] = None
    state["stored_outputs"] = {}
    state["workflow_status"] = "plan_ready" if (state.get("current_plan") or {}).get("steps") else "ready_for_analysis"
    _append_trace(state, step_name, "completed", {"replan_count": state.get("replan_count", 0)})
    return state


def best_effort_node(state: dict[str, Any]) -> dict[str, Any]:
    """Return the final best-effort answer when retry limits are exhausted."""

    step_name = "best_effort_node"
    _append_trace(state, step_name, "started", {"failure_summary": state.get("failure_summary", "")})
    state = build_best_effort_state(state)
    _append_trace(state, step_name, "completed", {"workflow_status": state.get("workflow_status", "")})
    state = analyze_workflow(state)
    return state


def _route_after_planner(state: dict[str, Any]) -> str:
    status = state.get("workflow_status")
    if status == "plan_ready":
        return "query_writer_node"
    if status == "best_effort":
        return "best_effort_node"
    return "analyzer_node"


def _route_after_executor(state: dict[str, Any]) -> str:
    status = state.get("workflow_status")
    if status in {"plan_ready", "retry_same_step"}:
        return "query_writer_node"
    if status == "needs_replan":
        return "replan_node"
    if status == "best_effort":
        return "best_effort_node"
    return "analyzer_node"


def _route_after_analyzer(state: dict[str, Any]) -> str:
    status = state.get("workflow_status")
    if status == "needs_replan":
        return "replan_node"
    if status == "best_effort":
        return "best_effort_node"
    return END


def _route_after_replan(state: dict[str, Any]) -> str:
    status = state.get("workflow_status")
    if status == "plan_ready":
        return "query_writer_node"
    if status == "best_effort":
        return "best_effort_node"
    return "analyzer_node"


@lru_cache(maxsize=1)
def build_graph():
    """Compile and cache the analytics workflow graph."""

    graph = StateGraph(AnalysisState)
    graph.add_node("load_schema_context_node", load_schema_context_node)
    graph.add_node("planner_node", planner_node)
    graph.add_node("query_writer_node", query_writer_node)
    graph.add_node("executor_node", executor_node)
    graph.add_node("analyzer_node", analyzer_node)
    graph.add_node("replan_node", replan_node)
    graph.add_node("best_effort_node", best_effort_node)

    graph.add_edge(START, "load_schema_context_node")
    graph.add_edge("load_schema_context_node", "planner_node")
    graph.add_conditional_edges("planner_node", _route_after_planner)
    graph.add_edge("query_writer_node", "executor_node")
    graph.add_conditional_edges("executor_node", _route_after_executor)
    graph.add_conditional_edges("analyzer_node", _route_after_analyzer)
    graph.add_conditional_edges("replan_node", _route_after_replan)
    graph.add_edge("best_effort_node", END)
    return graph.compile()
