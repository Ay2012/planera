"""Execution and orchestration tests for the staged workflow control flow."""

from __future__ import annotations

import pytest

from app.agent.graph import run_analysis
from app.config import get_settings
from app.data.registry import clear_source_registry, ingest_source
from app.data.semantic_model import clear_semantic_context_cache


@pytest.fixture(autouse=True)
def isolated_registry(tmp_path, monkeypatch):
    monkeypatch.setenv("REGISTRY_PATH", str(tmp_path / "executor_graph_registry.duckdb"))
    get_settings.cache_clear()
    clear_source_registry()
    clear_semantic_context_cache()
    yield
    clear_source_registry()
    clear_semantic_context_cache()
    get_settings.cache_clear()


def test_run_analysis_retries_one_failed_step_then_succeeds(monkeypatch) -> None:
    asset = ingest_source("pipeline.csv", b"owner,pipeline_velocity_days\nAda,10\nBen,14\n")

    class PlannerStub:
        def generate_json(self, prompt: str, schema=None):  # noqa: ANN001, ARG002
            return {
                "objective": "Summarize velocity by owner.",
                "can_answer_fully": True,
                "unsupported_requirements": [],
                "steps": [
                    {
                        "id": 1,
                        "purpose": "Summarize velocity by owner.",
                        "depends_on": [],
                        "output_alias": "velocity_by_owner",
                        "relations": [asset.primaryRelationName],
                        "required_columns": [
                            f"{asset.primaryRelationName}.owner",
                            f"{asset.primaryRelationName}.pipeline_velocity_days",
                        ],
                        "expected_output": "A grouped owner summary.",
                        "allow_empty_result": False,
                    }
                ],
                "max_steps": 3,
                "metric": "pipeline_velocity_days",
                "metric_direction": "lower_is_better",
            }

    class QueryWriterStub:
        def __init__(self) -> None:
            self.calls = 0

        def generate_json(self, prompt: str, schema=None):  # noqa: ANN001, ARG002
            self.calls += 1
            if self.calls == 1:
                return {
                    "step_id": 1,
                    "sql": f"SELECT sales_agent, AVG(pipeline_velocity_days) AS avg_velocity_days FROM {asset.primaryRelationName} GROUP BY sales_agent",
                    "explanation": "First attempt uses the wrong column name.",
                }
            return {
                "step_id": 1,
                "sql": f"SELECT owner, AVG(pipeline_velocity_days) AS avg_velocity_days FROM {asset.primaryRelationName} GROUP BY owner",
                "explanation": "Retry uses the available owner column.",
            }

    query_writer_stub = QueryWriterStub()
    monkeypatch.setattr("app.agent.planner.get_llm_client", lambda: PlannerStub())
    monkeypatch.setattr("app.agent.query_writer.get_llm_client", lambda: query_writer_stub)

    state = run_analysis("Which owners are slowest?", source_ids=[asset.id])

    assert query_writer_stub.calls == 2
    assert state["retry_counts"]["1"] == 1
    assert len(state["failure_history"]["1"]) == 1
    assert state["stored_outputs"]["velocity_by_owner"] is not None
    assert state["workflow_status"] == "complete"


def test_run_analysis_replans_once_after_second_failure(monkeypatch) -> None:
    asset = ingest_source("pipeline.csv", b"owner,pipeline_velocity_days\nAda,10\nBen,14\n")

    class PlannerStub:
        def __init__(self) -> None:
            self.calls = 0

        def generate_json(self, prompt: str, schema=None):  # noqa: ANN001, ARG002
            self.calls += 1
            if self.calls == 1:
                return {
                    "objective": "Try an owner summary.",
                    "can_answer_fully": True,
                    "unsupported_requirements": [],
                    "steps": [
                        {
                            "id": 1,
                            "purpose": "Broken owner summary.",
                            "depends_on": [],
                            "output_alias": "broken_summary",
                            "relations": [asset.primaryRelationName],
                            "required_columns": [f"{asset.primaryRelationName}.owner"],
                            "expected_output": "A broken output.",
                            "allow_empty_result": False,
                        }
                    ],
                    "max_steps": 3,
                    "metric": "",
                    "metric_direction": "",
                }
            return {
                "objective": "Fallback to a simple row count.",
                "can_answer_fully": True,
                "unsupported_requirements": [],
                "steps": [
                    {
                        "id": 1,
                        "purpose": "Count available rows.",
                        "depends_on": [],
                        "output_alias": "row_count",
                        "relations": [asset.primaryRelationName],
                        "required_columns": [f"{asset.primaryRelationName}.record_id"],
                        "expected_output": "A row count for best-effort answering.",
                        "allow_empty_result": False,
                    }
                ],
                "max_steps": 3,
                "metric": "",
                "metric_direction": "",
            }

    class QueryWriterStub:
        def __init__(self) -> None:
            self.calls = 0

        def generate_json(self, prompt: str, schema=None):  # noqa: ANN001, ARG002
            self.calls += 1
            if self.calls <= 2:
                return {
                    "step_id": 1,
                    "sql": f"SELECT sales_agent FROM {asset.primaryRelationName}",
                    "explanation": "This query will fail twice.",
                }
            return {
                "step_id": 1,
                "sql": f"SELECT COUNT(*) AS total_rows FROM {asset.primaryRelationName}",
                "explanation": "The replanned query succeeds.",
            }

    planner_stub = PlannerStub()
    query_writer_stub = QueryWriterStub()
    monkeypatch.setattr("app.agent.planner.get_llm_client", lambda: planner_stub)
    monkeypatch.setattr("app.agent.query_writer.get_llm_client", lambda: query_writer_stub)

    state = run_analysis("How much data is available?", source_ids=[asset.id])

    assert planner_stub.calls == 2
    assert state["replan_count"] == 1
    assert state["stored_outputs"]["row_count"] is not None
    assert state["workflow_status"] == "complete"


def test_run_analysis_returns_best_effort_after_replan_limit(monkeypatch) -> None:
    asset = ingest_source("pipeline.csv", b"owner,pipeline_velocity_days\nAda,10\nBen,14\n")

    class PlannerStub:
        def generate_json(self, prompt: str, schema=None):  # noqa: ANN001, ARG002
            return {
                "objective": "Keep trying the same unsupported summary.",
                "can_answer_fully": True,
                "unsupported_requirements": [],
                "steps": [
                    {
                        "id": 1,
                        "purpose": "Broken summary.",
                        "depends_on": [],
                        "output_alias": "broken_summary",
                        "relations": [asset.primaryRelationName],
                        "required_columns": [f"{asset.primaryRelationName}.owner"],
                        "expected_output": "A summary that keeps failing.",
                        "allow_empty_result": False,
                    }
                ],
                "max_steps": 3,
                "metric": "",
                "metric_direction": "",
            }

    class QueryWriterStub:
        def generate_json(self, prompt: str, schema=None):  # noqa: ANN001, ARG002
            return {
                "step_id": 1,
                "sql": f"SELECT sales_agent FROM {asset.primaryRelationName}",
                "explanation": "Always fails because sales_agent is unavailable.",
            }

    monkeypatch.setattr("app.agent.planner.get_llm_client", lambda: PlannerStub())
    monkeypatch.setattr("app.agent.query_writer.get_llm_client", lambda: QueryWriterStub())

    state = run_analysis("Which owners are slowest?", source_ids=[asset.id])

    assert state["replan_count"] == 1
    assert state["workflow_status"] == "complete"
    assert "## Best-effort answer" in state["analysis"]
    assert state["failure_summary"] != ""
