"""Planner and analysis contract tests with mocked LLM responses."""

from app.agent.analysis import run_analysis_narrative
from app.agent.planner import plan_next_step
from app.agent.state import create_initial_state


class FakeLLM:
    """Minimal stub for planner and analysis tests."""

    def generate_json(self, prompt: str):  # noqa: ANN001
        if '"action": "execute_step|finish"' in prompt:
            return {
                "intent": "diagnosis",
                "metric": "pipeline_velocity",
                "reasoning_summary": "Start with a current vs previous comparison.",
                "action": "execute_step",
                "step": {
                    "id": "step_1",
                    "kind": "sql",
                    "purpose": "Compare current and previous pipeline velocity.",
                    "input_views": ["opportunities_enriched"],
                    "code": "SELECT 1 AS value",
                    "output_alias": "comparison_result",
                    "expected_output": {"type": "table", "columns": ["value"]},
                    "success_criteria": ["query executes"],
                    "is_final_step": False,
                },
            }
        if '"analysis":' in prompt and "markdown" in prompt.lower():
            return {
                "analysis": "## Summary\nPipeline velocity improved from 69.77 to 66.14 days week over week.\n\n**Focus:** Enterprise Stage 2.",
            }
        return {"analysis": "Fallback analysis."}


def test_planner_returns_exact_executable_step(monkeypatch) -> None:
    monkeypatch.setattr("app.agent.planner.get_llm_client", lambda: FakeLLM())
    state = create_initial_state("Why did pipeline velocity drop this week?")
    state["dataset_context"] = {"reference_date": "2017-12-31", "views": [{"name": "opportunities_enriched"}]}
    state = plan_next_step(state)
    assert state["planner_action"] == "execute_step"
    assert state["current_step"]["kind"] == "sql"
    assert state["current_step"]["output_alias"] == "comparison_result"


def test_analysis_narrative_uses_llm(monkeypatch) -> None:
    monkeypatch.setattr("app.agent.analysis.get_llm_client", lambda: FakeLLM())
    state = create_initial_state("Why did pipeline velocity drop this week?")
    state["dataset_context"] = {"reference_date": "2017-12-31", "views": []}
    state["executed_steps"] = [{"id": "step_1", "purpose": "Compare", "status": "success", "output_alias": "comparison_result", "artifact": {"row_count": 2}}]
    state = run_analysis_narrative(state)
    assert "Pipeline velocity improved" in state["analysis"]
    assert "Enterprise" in state["analysis"]
