"""Planner and analysis contract tests with mocked LLM responses."""

from app.agent.analysis import run_analysis_narrative
from app.agent.planner import plan_compiled_query
from app.agent.state import create_initial_state


class FakeLLM:
    """Minimal stub for planner and analysis tests."""

    def generate_json(self, prompt: str, schema=None):  # noqa: ANN001, ARG002
        if '"max_steps": 3' in prompt and "metric_direction" in prompt:
            return {
                "objective": "Compare current and previous pipeline velocity.",
                "plan": [
                    {
                        "id": 1,
                        "purpose": "Compare current and previous pipeline velocity.",
                        "type": "sql",
                        "query": "SELECT 'Previous Week' AS period, 2 AS pipeline_velocity UNION ALL SELECT 'Current Week' AS period, 1 AS pipeline_velocity",
                        "expectation": {
                            "step_category": "premise_check",
                            "comparison_type": "period_comparison",
                            "expected_grouping_columns": [],
                            "expected_metric_columns": ["pipeline_velocity"],
                            "expected_period_column": "period",
                            "min_expected_rows": 2,
                            "requires_distinct_periods": True,
                            "preserve_population_from_step_id": None,
                        },
                        "output_alias": "comparison_result",
                    }
                ],
                "max_steps": 3,
                "metric": "pipeline_velocity",
                "metric_direction": "lower_is_better",
            }
        if '"analysis_markdown": string' in prompt and "approved claims" in prompt.lower():
            return {
                "answer_status": "answered",
                "analysis_markdown": "## Summary\nThe available evidence shows value = 1 for SMB.",
                "used_claim_ids": ["claim_comparison_result_row_1"],
            }
        return {
            "answer_status": "insufficient_evidence",
            "analysis_markdown": "The approved claims are insufficient to answer the question.",
            "used_claim_ids": [],
        }


class LeakyAnalysisLLM:
    """Return deliberately invalid rendered analysis to exercise fallback handling."""

    def generate_json(self, prompt: str, schema=None):  # noqa: ANN001, ARG002
        if '"analysis_markdown": string' in prompt and "approved claims" in prompt.lower():
            return {
                "answer_status": "answered",
                "analysis_markdown": "Validator exception. Review executed steps and trace for raw outputs.",
                "used_claim_ids": ["claim_premise_check"],
            }
        return {
            "answer_status": "insufficient_evidence",
            "analysis_markdown": "The approved claims are insufficient to answer the question.",
            "used_claim_ids": [],
        }


def test_planner_returns_compiled_plan(monkeypatch) -> None:
    monkeypatch.setattr("app.agent.planner.get_llm_client", lambda: FakeLLM())
    state = create_initial_state("Why did pipeline velocity drop this week?")
    state["dataset_context"] = {
        "reference_date": "2017-12-31",
        "relations": [
            {
                "name": "opportunities_enriched",
                "columns": [
                    {"name": "period", "dtype": "object", "type_family": "string", "field_origin": "derived", "derived_from": [], "semantic_hints": ["period"]},
                    {
                        "name": "pipeline_velocity",
                        "dtype": "int64",
                        "type_family": "number",
                        "field_origin": "derived",
                        "derived_from": [],
                        "semantic_hints": ["pipeline velocity"],
                    },
                ],
                "identifier_columns": [],
                "time_columns": [],
                "measure_columns": ["pipeline_velocity"],
                "dimension_columns": ["period"],
                "semantic_mappings": [],
                "grain": "Rows can be keyed by period",
            }
        ],
        "relationships": [],
        "views": [{"name": "opportunities_enriched"}],
    }
    state = plan_compiled_query(state)
    assert state["compiled_plan"] is not None
    assert state["compiled_plan"]["plan"][0]["type"] == "sql"
    assert "SELECT 'Previous Week'" in state["compiled_plan"]["plan"][0]["query"]
    assert state["compiled_plan"]["plan"][0]["output_alias"] == "comparison_result"
    assert state["compiled_plan"]["plan"][0]["expectation"]["step_category"] == "premise_check"


def test_analysis_narrative_uses_llm(monkeypatch) -> None:
    monkeypatch.setattr("app.agent.analysis.get_llm_client", lambda: FakeLLM())
    state = create_initial_state("Why did pipeline velocity drop this week?")
    state["dataset_context"] = {"reference_date": "2017-12-31", "views": []}
    state["compiled_plan"] = {"objective": "Test", "metric": "", "metric_direction": ""}
    state["executed_steps"] = [
        {
            "id": "step_1",
            "purpose": "Compare",
            "status": "success",
            "validation_status": "valid",
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
    assert "value = 1" in state["analysis"]
    assert "SMB" in state["analysis"]


def test_analysis_narrative_preserves_partial_evidence_without_leaking_internal_text(monkeypatch) -> None:
    monkeypatch.setattr("app.agent.analysis.get_llm_client", lambda: LeakyAnalysisLLM())
    state = create_initial_state("Why did pipeline velocity drop this week?")
    state["metric"] = "avg_pipeline_velocity_days"
    state["compiled_plan"] = {"objective": "Test", "metric": "avg_pipeline_velocity_days", "metric_direction": "lower_is_better"}
    state["executed_steps"] = [
        {
            "id": "step_1",
            "purpose": "Compare weekly metrics",
            "status": "success",
            "validation_status": "valid",
            "output_alias": "weekly_pipeline_metrics",
            "artifact": {
                "alias": "weekly_pipeline_metrics",
                "row_count": 2,
                "columns": ["period", "avg_pipeline_velocity_days"],
                "preview_rows": [
                    {"period": "Previous Week", "avg_pipeline_velocity_days": 69.94},
                    {"period": "Current Week", "avg_pipeline_velocity_days": 64.13},
                ],
                "summary": {},
            },
        },
        {
            "id": "step_2",
            "purpose": "Break velocity out by owner",
            "status": "failed",
            "output_alias": "owner_velocity",
            "error": "Binder error",
        },
    ]

    state = run_analysis_narrative(state)

    assert state["answer_status"] == "contradicted_premise"
    assert state["analysis"].startswith("The premise is not supported.")
    assert "validator" not in state["analysis"].lower()
    assert "trace for raw outputs" not in state["analysis"].lower()


def test_analysis_narrative_uses_clean_specific_fallback_for_failed_repaired_premise_check() -> None:
    state = create_initial_state("Why did pipeline velocity drop this week?")
    state["compiled_plan"] = {
        "objective": "Compare weekly velocity",
        "metric": "pipeline_velocity_days",
        "metric_direction": "lower_is_better",
    }
    state["executed_steps"] = [
        {
            "id": "step_1",
            "purpose": "Compare weekly pipeline velocity.",
            "status": "invalid",
            "attempt": 2,
            "validation_status": "invalid",
            "validation_reason": "The result is missing expected columns: avg_pipeline_velocity_days.",
            "expectation": {
                "step_category": "premise_check",
                "comparison_type": "period_comparison",
                "expected_grouping_columns": [],
                "expected_metric_columns": ["avg_pipeline_velocity_days"],
                "expected_period_column": "period",
                "min_expected_rows": 2,
                "requires_distinct_periods": True,
                "preserve_population_from_step_id": None,
            },
            "output_alias": "velocity_comparison",
            "error": "The result is missing expected columns: avg_pipeline_velocity_days.",
        }
    ]

    state = run_analysis_narrative(state)

    assert state["answer_status"] == "insufficient_evidence"
    assert "repaired premise-check query did not return the required metric avg_pipeline_velocity_days" in state["analysis"]
    assert "missing expected columns" not in state["analysis"].lower()
    assert "validator" not in state["analysis"].lower()
