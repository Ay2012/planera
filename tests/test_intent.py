"""Planner and analyzer contract tests with mocked LLM responses."""

from __future__ import annotations

from app.agent.analysis import run_analysis_narrative
from app.agent.planner import plan_analysis
from app.agent.state import create_initial_state


class FakeLLM:
    """Minimal stub for planner and analyzer tests."""

    def generate_json(self, prompt: str, schema=None):  # noqa: ANN001, ARG002
        if '"max_steps": 3' in prompt and '"steps"' in prompt:
            return {
                "objective": "Compare current and previous pipeline velocity with one bounded step.",
                "can_answer_fully": True,
                "unsupported_requirements": [],
                "steps": [
                    {
                        "id": 1,
                        "purpose": "Summarize the metric by period.",
                        "depends_on": [],
                        "output_alias": "comparison_result",
                        "relations": ["opportunities_enriched"],
                        "required_columns": ["opportunities_enriched.pipeline_velocity_days"],
                        "expected_output": "A table with the grouped metric.",
                        "allow_empty_result": False,
                    }
                ],
                "max_steps": 3,
                "metric": "pipeline_velocity_days",
                "metric_direction": "lower_is_better",
            }
        if '"decision": "final_answer" | "replan"' in prompt:
            return {
                "decision": "final_answer",
                "summary": "The workflow produced a usable final output.",
                "key_findings": ["1 row was returned by the final step."],
                "important_metrics": [{"label": "row_count", "value": "1"}],
                "caveats": [],
                "final_answer": "## Summary\nThe final step returned 1 row in comparison_result.",
                "failure_summary": "",
            }
        return {
            "decision": "replan",
            "summary": "The current outputs are incomplete.",
            "key_findings": [],
            "important_metrics": [],
            "caveats": [],
            "final_answer": "",
            "failure_summary": "The collected outputs were incomplete.",
        }


def test_planner_returns_full_non_sql_plan(monkeypatch) -> None:
    monkeypatch.setattr("app.agent.planner.get_llm_client", lambda: FakeLLM())
    state = create_initial_state("Why did pipeline velocity drop this week?")
    state["dataset_context"] = {
        "reference_date": "2017-12-31",
        "source": "source_registry",
        "dialect": "duckdb",
        "relations": [
            {
                "name": "opportunities_enriched",
                "source_id": "source_1",
                "source_name": "opportunities.csv",
                "is_primary": True,
                "row_count": 10,
                "grain": "One row per opportunity",
                "identifier_columns": ["record_id"],
                "time_columns": [],
                "measure_columns": ["pipeline_velocity_days"],
                "dimension_columns": [],
                "join_keys": [],
                "semantic_mappings": [],
                "columns": [
                    {
                        "name": "pipeline_velocity_days",
                        "dtype": "DOUBLE",
                        "type_family": "number",
                        "nullable": True,
                        "semantic_hints": ["pipeline velocity"],
                    }
                ],
            }
        ],
    }
    state = plan_analysis(state)
    assert state["current_plan"] is not None
    assert state["current_plan"]["steps"][0]["output_alias"] == "comparison_result"
    assert "query" not in state["current_plan"]["steps"][0]


def test_analysis_narrative_uses_llm(monkeypatch) -> None:
    monkeypatch.setattr("app.agent.analysis.get_llm_client", lambda: FakeLLM())
    state = create_initial_state("Why did pipeline velocity drop this week?")
    state["schema_context_summary"] = {"reference_date": "2017-12-31", "relations": []}
    state["current_plan"] = {"objective": "Test", "metric": "", "metric_direction": "", "steps": []}
    state["workflow_status"] = "ready_for_analysis"
    state["executed_steps"] = [
        {
            "id": "step_1",
            "purpose": "Compare",
            "status": "success",
            "output_alias": "comparison_result",
            "artifact": {
                "alias": "comparison_result",
                "row_count": 1,
                "columns": ["segment", "value"],
                "preview_rows": [{"segment": "SMB", "value": 1}],
                "summary": {},
            },
        }
    ]
    state = run_analysis_narrative(state)
    assert "comparison_result" in state["analysis"]
    assert state["workflow_status"] == "complete"
