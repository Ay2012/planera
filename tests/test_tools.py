"""Executor tests for compiled SQL plans."""

import pytest

from app.agent.executor import execute_plan, execute_single_plan_step
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
    compiled_plan = {
        "objective": "Segment counts",
        "max_steps": 3,
        "plan": [
            {
                "id": 1,
                "purpose": "Get one sample aggregation.",
                "type": "sql",
                "query": f"SELECT segment, COUNT(*) AS deals FROM {asset.primaryRelationName} GROUP BY segment ORDER BY deals DESC",
                "output_alias": "segment_counts",
            }
        ],
    }
    outcome = execute_plan(state, compiled_plan)
    assert outcome["status"] == "success"
    last = state["executed_steps"][-1]
    assert last["status"] == "success"
    assert last["artifact"]["row_count"] > 0
    assert "segment" in last["artifact"]["columns"]


def test_execute_plan_marks_empty_table_as_failed() -> None:
    asset = ingest_source("pipeline.csv", b"segment\nSMB\nEnterprise\n")
    state = create_initial_state("Why did pipeline velocity drop this week?")
    state["dataset_context"] = get_semantic_context([asset.id]).schema_manifest
    compiled_plan = {
        "objective": "Empty query",
        "max_steps": 3,
        "plan": [
            {
                "id": 1,
                "purpose": "Return no rows.",
                "type": "sql",
                "query": "SELECT 1 WHERE 1=0",
                "output_alias": "empty_result",
            }
        ],
    }
    outcome = execute_plan(state, compiled_plan)
    assert outcome["status"] == "failed"
    assert state["executed_steps"][-1]["status"] == "failed"


def test_execute_single_plan_step_retry() -> None:
    asset = ingest_source("pipeline.csv", b"segment\nSMB\nEnterprise\n")
    state = create_initial_state("Test retry")
    state["dataset_context"] = get_semantic_context([asset.id]).schema_manifest
    step = {
        "id": 1,
        "purpose": "Get one row.",
        "type": "sql",
        "query": "SELECT 1 AS value",
        "output_alias": "r1",
    }
    out = execute_single_plan_step(state, step, attempt=2)
    assert out["status"] == "success"
    assert state["executed_steps"][-1]["attempt"] == 2
