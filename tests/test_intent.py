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
                        "query": "SELECT 1 AS value",
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


def test_planner_returns_compiled_plan(monkeypatch) -> None:
    monkeypatch.setattr("app.agent.planner.get_llm_client", lambda: FakeLLM())
    state = create_initial_state("Why did pipeline velocity drop this week?")
    state["dataset_context"] = {"reference_date": "2017-12-31", "views": [{"name": "opportunities_enriched"}]}
    state = plan_compiled_query(state)
    assert state["compiled_plan"] is not None
    assert state["compiled_plan"]["plan"][0]["type"] == "sql"
    assert state["compiled_plan"]["plan"][0]["query"] == "SELECT 1 AS value"
    assert state["compiled_plan"]["plan"][0]["output_alias"] == "comparison_result"


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
