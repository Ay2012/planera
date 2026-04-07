"""Planner-input contract tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.agent.planner import _schema_subset_for_question, build_planner_input, get_llm_client, plan_compiled_query, repair_failed_step
from app.config import get_settings
from app.data.registry import clear_source_registry, ingest_source
from app.data.semantic_model import clear_semantic_context_cache
from app.schemas import CompiledPlan


@pytest.fixture(autouse=True)
def isolated_registry(tmp_path, monkeypatch):
    monkeypatch.setenv("REGISTRY_PATH", str(tmp_path / "planner_source_registry.duckdb"))
    get_settings.cache_clear()
    clear_source_registry()
    clear_semantic_context_cache()
    yield
    clear_source_registry()
    clear_semantic_context_cache()
    get_settings.cache_clear()


def test_compiled_plan_normalizes_max_steps() -> None:
    plan = CompiledPlan.model_validate(
        {
            "objective": "Test",
            "plan": [
                {
                    "id": 1,
                    "purpose": "One step",
                    "type": "sql",
                    "query": "SELECT 1",
                }
            ],
            "max_steps": 1,
            "metric": "",
            "metric_direction": "",
        }
    )
    assert plan.max_steps == 3


def test_build_planner_input_keeps_sources_separate_by_source_id() -> None:
    first = ingest_source("orders.csv", b"order_id,amount\no1,100\n")
    second = ingest_source("orders.csv", b"order_id,amount\no2,250\n")

    planner_input = build_planner_input("Compare both uploads.", [first.id, second.id])

    assert len(planner_input.sources) == 2
    assert {source.source_id for source in planner_input.sources} == {first.id, second.id}
    assert all(len(source.tables) == 1 for source in planner_input.sources)


def test_pipeline_velocity_field_is_treated_by_generic_structural_rules() -> None:
    asset = ingest_source("pipeline.csv", b"owner,pipeline_velocity_days,created_at\nAda,10,2026-01-01\nBen,14,2026-01-02\n")

    planner_input = build_planner_input("Why did velocity change?", [asset.id])
    table = planner_input.sources[0].tables[0]
    role_by_name = {column.column_name: column.semantic_role for column in table.columns}

    assert role_by_name["pipeline_velocity_days"] == "measure"
    assert role_by_name["created_at"] == "time"
    assert "semantic_mappings" not in planner_input.model_dump_json()


def test_planner_input_module_does_not_import_legacy_gtm_modules() -> None:
    module_source = (Path(__file__).resolve().parents[1] / "app" / "data" / "planner_input.py").read_text()

    assert "app.data.loader" not in module_source
    assert "app.data.transforms" not in module_source
    assert "app.data.mock_data" not in module_source
    assert "app.utils.constants" not in module_source


def test_legacy_planner_runtime_entrypoints_raise_not_implemented() -> None:
    with pytest.raises(NotImplementedError, match="Planner LLM access"):
        get_llm_client()

    with pytest.raises(NotImplementedError, match="Compiled planner runtime"):
        plan_compiled_query({"query": "test"})

    with pytest.raises(NotImplementedError, match="Planner repair runtime"):
        repair_failed_step({}, {})

    with pytest.raises(NotImplementedError, match="Trimmed schema subsets"):
        _schema_subset_for_question({"relations": []}, "Which fields matter?")
