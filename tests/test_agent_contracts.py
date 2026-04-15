"""Contract and scaffolding tests for the staged agent runtime restoration."""

from __future__ import annotations

from app.agent.state import create_initial_state
from app.api.workspace import STEP_LABELS
from app.schemas import AnalysisPlan, AnalyzerDecision, GeneratedQuery


def test_analysis_plan_normalizes_max_steps() -> None:
    plan = AnalysisPlan.model_validate(
        {
            "objective": "Answer the question with available uploads.",
            "can_answer_fully": True,
            "unsupported_requirements": [],
            "steps": [
                {
                    "id": 1,
                    "purpose": "Compute a grouped summary.",
                    "depends_on": [],
                    "output_alias": "grouped_summary",
                    "relations": ["orders_source_1234"],
                    "required_columns": ["orders_source_1234.amount"],
                    "expected_output": "A grouped table for downstream use.",
                    "allow_empty_result": False,
                }
            ],
            "max_steps": 1,
            "metric": "amount",
            "metric_direction": "higher_is_better",
        }
    )

    assert plan.max_steps == 3


def test_generated_query_requires_one_sql_string() -> None:
    query = GeneratedQuery.model_validate(
        {
            "step_id": 2,
            "sql": "SELECT 1 AS value",
            "explanation": "Returns a placeholder row for the current step.",
        }
    )

    assert query.step_id == 2
    assert query.sql == "SELECT 1 AS value"


def test_analyzer_decision_supports_replan_shape() -> None:
    decision = AnalyzerDecision.model_validate(
        {
            "decision": "replan",
            "summary": "The current outputs only answer part of the question.",
            "key_findings": [],
            "important_metrics": [],
            "caveats": ["A required relationship was not available."],
            "final_answer": "",
            "failure_summary": "Required relationship not present in schema/context.",
        }
    )

    assert decision.decision == "replan"
    assert decision.failure_summary != ""


def test_create_initial_state_exposes_new_workflow_fields() -> None:
    state = create_initial_state("How many orders are overdue?", source_ids=["source_123"])

    assert state["query"] == "How many orders are overdue?"
    assert state["source_ids"] == ["source_123"]
    assert state["schema_context_summary"] == {}
    assert state["current_plan"] is None
    assert state["stored_outputs"] == {}
    assert state["step_queries"] == {}
    assert state["failure_history"] == {}
    assert state["retry_counts"] == {}
    assert state["replan_count"] == 0
    assert state["trace"] == []
    assert state["executed_steps"] == []
    assert state["errors"] == []


def test_workspace_step_labels_include_new_workflow_nodes() -> None:
    assert STEP_LABELS["planner_node"] == "Workflow Planning"
    assert STEP_LABELS["query_writer_node"] == "Query Writing"
    assert STEP_LABELS["executor_node"] == "Step Execution"
    assert STEP_LABELS["analyzer_node"] == "Final Analysis"
    assert STEP_LABELS["replan_node"] == "Replanning"
    assert STEP_LABELS["best_effort_node"] == "Best Effort Answer"
