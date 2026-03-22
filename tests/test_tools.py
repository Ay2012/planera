"""Executor and review tests."""

from app.agent.executor import execute_current_step
from app.agent.reviewer import review_last_step
from app.agent.state import create_initial_state
from app.data.semantic_model import get_semantic_context


def test_execute_sql_step_returns_artifact_summary() -> None:
    state = create_initial_state("Compare SMB vs Enterprise performance")
    state["dataset_context"] = get_semantic_context().schema_manifest
    state["current_step"] = {
        "id": "step_sql_1",
        "kind": "sql",
        "purpose": "Get one sample row.",
        "input_views": ["opportunities_enriched"],
        "code": "SELECT segment, COUNT(*) AS deals FROM opportunities_enriched GROUP BY segment ORDER BY deals DESC",
        "output_alias": "segment_counts",
        "expected_output": {"type": "table", "columns": ["segment", "deals"]},
        "success_criteria": ["query executes"],
        "is_final_step": False,
    }
    state = execute_current_step(state)
    last = state["executed_steps"][-1]
    assert last["status"] == "success"
    assert last["artifact"]["row_count"] > 0
    assert "segment" in last["artifact"]["columns"]


def test_review_marks_empty_table_as_failed() -> None:
    state = create_initial_state("Why did pipeline velocity drop this week?")
    state["current_step"] = {
        "id": "step_sql_empty",
        "kind": "sql",
        "purpose": "Return no rows.",
        "input_views": ["opportunities_enriched"],
        "code": "SELECT 1 WHERE 1=0",
        "output_alias": "empty_result",
        "expected_output": {"type": "table", "columns": ["1"]},
        "success_criteria": ["query executes"],
        "is_final_step": False,
    }
    state["executed_steps"] = [
        {
            "id": "step_sql_empty",
            "kind": "sql",
            "purpose": "Return no rows.",
            "code": "SELECT 1 WHERE 1=0",
            "output_alias": "empty_result",
            "attempt": 1,
            "status": "success",
            "artifact": {"alias": "empty_result", "artifact_type": "table", "row_count": 0, "columns": ["1"], "preview_rows": [], "summary": {}},
            "error": None,
        }
    ]
    state = review_last_step(state)
    assert state["executed_steps"][-1]["status"] == "failed"
    assert state["retry_count"] == 1
