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
        if '"analysis":' in prompt and "markdown" in prompt.lower():
            return {
                "analysis": "## Summary\nPipeline velocity improved from 69.77 to 66.14 days week over week.\n\n**Focus:** Enterprise Stage 2.",
            }
        return {"analysis": "Fallback analysis."}


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
    state["executed_steps"] = [{"id": "step_1", "purpose": "Compare", "status": "success", "output_alias": "comparison_result", "artifact": {"row_count": 2}}]
    state = run_analysis_narrative(state)
    assert "Pipeline velocity improved" in state["analysis"]
    assert "Enterprise" in state["analysis"]
