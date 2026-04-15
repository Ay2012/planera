"""Executor tests for the step-by-step SQL runtime."""

from __future__ import annotations

import pytest

from app.agent.executor import execute_current_step
from app.agent.state import create_initial_state
from app.config import get_settings
from app.data.registry import clear_source_registry, ingest_source
from app.data.semantic_model import clear_semantic_context_cache, get_semantic_context


@pytest.fixture(autouse=True)
def isolated_registry(tmp_path, monkeypatch):
    monkeypatch.setenv("REGISTRY_PATH", str(tmp_path / "tools_source_registry.duckdb"))
    get_settings.cache_clear()
    clear_source_registry()
    clear_semantic_context_cache()
    yield
    clear_source_registry()
    clear_semantic_context_cache()
    get_settings.cache_clear()


def test_execute_sql_step_returns_artifact_summary() -> None:
    asset = ingest_source("pipeline.csv", b"segment\nSMB\nEnterprise\nSMB\n")
    state = create_initial_state("Compare SMB vs Enterprise performance")
    state["dataset_context"] = get_semantic_context([asset.id]).schema_manifest
    state["current_plan"] = {
        "objective": "Segment counts",
        "steps": [
            {
                "id": 1,
                "purpose": "Get one sample aggregation.",
                "output_alias": "segment_counts",
                "depends_on": [],
                "relations": [asset.primaryRelationName],
                "required_columns": [f"{asset.primaryRelationName}.segment"],
                "expected_output": "A grouped segment count table.",
                "allow_empty_result": False,
            }
        ],
    }
    state["generated_query"] = {
        "step_id": 1,
        "sql": f"SELECT segment, COUNT(*) AS deals FROM {asset.primaryRelationName} GROUP BY segment ORDER BY deals DESC",
        "explanation": "Counts rows by segment.",
    }
    outcome = execute_current_step(state)
    assert outcome["workflow_status"] == "ready_for_analysis"
    last = state["executed_steps"][-1]
    assert last["status"] == "success"
    assert last["artifact"]["row_count"] > 0
    assert "segment" in last["artifact"]["columns"]


def test_execute_plan_marks_empty_table_as_failed() -> None:
    asset = ingest_source("pipeline.csv", b"segment\nSMB\nEnterprise\n")
    state = create_initial_state("Why did pipeline velocity drop this week?")
    state["dataset_context"] = get_semantic_context([asset.id]).schema_manifest
    state["current_plan"] = {
        "objective": "Empty query",
        "steps": [
            {
                "id": 1,
                "purpose": "Return no rows.",
                "output_alias": "empty_result",
                "depends_on": [],
                "relations": [asset.primaryRelationName],
                "required_columns": [f"{asset.primaryRelationName}.segment"],
                "expected_output": "An intentionally empty result.",
                "allow_empty_result": False,
            }
        ],
    }
    state["generated_query"] = {
        "step_id": 1,
        "sql": "SELECT 1 WHERE 1=0",
        "explanation": "Returns no rows.",
    }
    outcome = execute_current_step(state)
    assert outcome["workflow_status"] == "retry_same_step"
    assert state["executed_steps"][-1]["status"] == "failed"


def test_execute_current_step_retry_attempt_is_recorded() -> None:
    asset = ingest_source("pipeline.csv", b"segment\nSMB\nEnterprise\n")
    state = create_initial_state("Test retry")
    state["dataset_context"] = get_semantic_context([asset.id]).schema_manifest
    state["current_plan"] = {
        "steps": [
            {
                "id": 1,
                "purpose": "Get one row.",
                "output_alias": "r1",
                "depends_on": [],
                "relations": [asset.primaryRelationName],
                "required_columns": [],
                "expected_output": "A single-row output.",
                "allow_empty_result": False,
            }
        ]
    }
    state["retry_counts"]["1"] = 1
    state["generated_query"] = {
        "step_id": 1,
        "sql": "SELECT 1 AS value",
        "explanation": "Returns one row.",
    }
    out = execute_current_step(state)
    assert out["workflow_status"] == "ready_for_analysis"
    assert state["executed_steps"][-1]["attempt"] == 2
