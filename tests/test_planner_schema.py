"""Planner schema and compact context behavior."""

from __future__ import annotations

import pytest

from app.agent.planner import build_compact_schema_context, plan_analysis
from app.agent.state import create_initial_state
from app.config import get_settings
from app.data.registry import clear_source_registry, ingest_source
from app.data.semantic_model import clear_semantic_context_cache, get_semantic_context
from app.schemas import AnalysisPlan


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


def test_analysis_plan_normalizes_max_steps() -> None:
    plan = AnalysisPlan.model_validate(
        {
            "objective": "Test the planner contract",
            "can_answer_fully": True,
            "unsupported_requirements": [],
            "steps": [
                {
                    "id": 1,
                    "purpose": "One step",
                    "depends_on": [],
                    "output_alias": "sample_output",
                    "relations": ["sample_relation"],
                    "required_columns": ["sample_relation.value"],
                    "expected_output": "One simple result.",
                    "allow_empty_result": False,
                }
            ],
            "max_steps": 1,
            "metric": "",
            "metric_direction": "",
        }
    )
    assert plan.max_steps == 3


def test_plan_analysis_stores_current_plan(monkeypatch) -> None:
    class PlannerLLM:
        def generate_json(self, prompt: str, schema=None):  # noqa: ANN001, ARG002
            return {
                "objective": "Count by segment",
                "can_answer_fully": True,
                "unsupported_requirements": [],
                "steps": [
                    {
                        "id": 1,
                        "purpose": "Count by segment",
                        "depends_on": [],
                        "output_alias": "counts",
                        "relations": ["segments_source_1234"],
                        "required_columns": ["segments_source_1234.segment"],
                        "expected_output": "A grouped count table.",
                        "allow_empty_result": False,
                    }
                ],
                "max_steps": 3,
                "metric": "",
                "metric_direction": "",
            }

    monkeypatch.setattr("app.agent.planner.get_llm_client", lambda: PlannerLLM())

    state = create_initial_state("Compare segments")
    state["dataset_context"] = {"reference_date": "2017-12-31", "source": "", "dialect": "duckdb", "relations": []}
    state = plan_analysis(state)

    assert state["current_plan"] is not None
    assert len(state["current_plan"]["steps"]) == 1


def test_semantic_context_exposes_normalized_manifest() -> None:
    asset = ingest_source("pipeline.csv", b"owner,pipeline_velocity_days\nAda,10\nBen,14\n")
    manifest = get_semantic_context().schema_manifest

    assert manifest["dialect"] == "duckdb"
    assert manifest["relations"]
    relation = next(relation for relation in manifest["relations"] if relation["name"] == asset.primaryRelationName)
    assert relation["columns"]
    assert relation["identifier_columns"]
    assert relation["grain"]


def test_compact_schema_context_exposes_relevant_relation() -> None:
    asset = ingest_source("pipeline.csv", b"owner,pipeline_velocity_days\nAda,10\nBen,14\n")
    compact = build_compact_schema_context(
        get_semantic_context([asset.id]).schema_manifest,
        "Why did pipeline velocity change by owner?",
    )

    assert compact["relations"]
    assert compact["relations"][0]["name"] == asset.primaryRelationName
    assert any(column["name"] == "owner" for column in compact["relations"][0]["columns"])
