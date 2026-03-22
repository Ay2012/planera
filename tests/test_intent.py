"""Planner and synthesis contract tests with mocked Gemini responses."""

from app.agent.planner import plan_next_step
from app.agent.recommender import build_recommendation
from app.agent.state import create_initial_state
from app.agent.synthesizer import synthesize_findings


class FakeGemini:
    """Minimal Gemini stub for planner/synthesis/recommendation tests."""

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
        if '"summary": "..."' in prompt:
            return {
                "summary": "Pipeline velocity improved from 69.77 to 66.14 days week over week.",
                "root_cause": "Enterprise remains the slowest segment with Stage 2 as the largest open-pipeline bottleneck.",
                "recommendation": "Focus managers on Enterprise Stage 2 opportunities first.",
            }
        return {"recommendation": "Focus managers on Enterprise Stage 2 opportunities first."}


def test_planner_returns_exact_executable_step(monkeypatch) -> None:
    monkeypatch.setattr("app.agent.planner.get_llm_client", lambda: FakeGemini())
    state = create_initial_state("Why did pipeline velocity drop this week?")
    state["dataset_context"] = {"reference_date": "2017-12-31", "views": [{"name": "opportunities_enriched"}]}
    state = plan_next_step(state)
    assert state["planner_action"] == "execute_step"
    assert state["current_step"]["kind"] == "sql"
    assert state["current_step"]["output_alias"] == "comparison_result"


def test_synthesis_and_recommendation_use_llm(monkeypatch) -> None:
    monkeypatch.setattr("app.agent.synthesizer.get_llm_client", lambda: FakeGemini())
    monkeypatch.setattr("app.agent.recommender.get_llm_client", lambda: FakeGemini())
    state = create_initial_state("Why did pipeline velocity drop this week?")
    state["evidence"] = [{"label": "current_velocity", "value": 66.14}, {"label": "previous_velocity", "value": 69.77}]
    state["executed_steps"] = [{"id": "step_1", "purpose": "Compare", "status": "success", "output_alias": "comparison_result", "artifact": {"row_count": 2}}]
    state = synthesize_findings(state)
    state = build_recommendation(state)
    assert "Pipeline velocity improved" in state["summary"]
    assert "Enterprise" in state["root_cause"]
    assert "Enterprise Stage 2" in state["recommendation"]
