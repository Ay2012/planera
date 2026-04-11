"""Analyzer behavior tests for the final workflow interface."""

from __future__ import annotations

from app.agent.analysis import analyze_workflow
from app.agent.state import create_initial_state


def test_analyzer_returns_final_answer_when_llm_succeeds(monkeypatch) -> None:
    class FakeAnalyzerLLM:
        def generate_json(self, prompt: str, schema=None):  # noqa: ANN001, ARG002
            return {
                "decision": "final_answer",
                "summary": "The workflow produced a grounded answer.",
                "key_findings": ["The final output contains 2 rows."],
                "important_metrics": [{"label": "row_count", "value": "2"}],
                "caveats": [],
                "final_answer": "## Summary\nThe final output contains 2 rows.",
                "failure_summary": "",
            }

    monkeypatch.setattr("app.agent.analysis.get_llm_client", lambda: FakeAnalyzerLLM())

    state = create_initial_state("What happened?")
    state["workflow_status"] = "ready_for_analysis"
    state["schema_context_summary"] = {"reference_date": "", "relations": []}
    state["current_plan"] = {"objective": "Test", "steps": []}
    state["executed_steps"] = [
        {
            "id": "1",
            "status": "success",
            "purpose": "Summarize rows",
            "output_alias": "final_output",
            "artifact": {"alias": "final_output", "row_count": 2, "columns": ["value"], "preview_rows": [{"value": 1}], "summary": {}},
        }
    ]

    state = analyze_workflow(state)

    assert state["workflow_status"] == "complete"
    assert "2 rows" in state["analysis"]


def test_analyzer_requests_replan_when_outputs_are_incomplete(monkeypatch) -> None:
    class FakeAnalyzerLLM:
        def generate_json(self, prompt: str, schema=None):  # noqa: ANN001, ARG002
            return {
                "decision": "replan",
                "summary": "The outputs do not answer the question yet.",
                "key_findings": [],
                "important_metrics": [],
                "caveats": [],
                "final_answer": "",
                "failure_summary": "Final results answered only part of the user question.",
            }

    monkeypatch.setattr("app.agent.analysis.get_llm_client", lambda: FakeAnalyzerLLM())

    state = create_initial_state("What happened?")
    state["workflow_status"] = "ready_for_analysis"
    state["schema_context_summary"] = {"reference_date": "", "relations": []}
    state["current_plan"] = {"objective": "Test", "steps": []}

    state = analyze_workflow(state)

    assert state["workflow_status"] == "needs_replan"
    assert state["failure_summary"] == "Final results answered only part of the user question."


def test_analyzer_returns_best_effort_after_limits(monkeypatch) -> None:
    class FakeAnalyzerLLM:
        def generate_json(self, prompt: str, schema=None):  # noqa: ANN001, ARG002
            return {
                "decision": "final_answer",
                "summary": "Returning the best-effort answer.",
                "key_findings": [],
                "important_metrics": [],
                "caveats": ["Requested relationship was unavailable."],
                "final_answer": "## Best-effort answer\nAnswered parts:\n- Captured 1 row.\n\nCould not answer completely:\n- Requested relationship was unavailable.",
                "failure_summary": "",
            }

    monkeypatch.setattr("app.agent.analysis.get_llm_client", lambda: FakeAnalyzerLLM())

    state = create_initial_state("What happened?")
    state["workflow_status"] = "best_effort_ready"
    state["schema_context_summary"] = {"reference_date": "", "relations": []}
    state["current_plan"] = {"objective": "Test", "steps": []}
    state["final_answer"] = "## Best-effort answer\nAnswered parts:\n- Captured 1 row."
    state["failure_summary"] = "Requested relationship was unavailable."

    state = analyze_workflow(state)

    assert state["workflow_status"] == "complete"
    assert "## Best-effort answer" in state["analysis"]
