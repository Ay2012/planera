"""Compiled plan schema and planner retry behavior."""

import pytest

from app.agent.planner import plan_compiled_query
from app.agent.state import create_initial_state
from app.config import get_settings
from app.data.registry import clear_source_registry, ingest_source
from app.data.semantic_model import clear_semantic_context_cache, get_semantic_context
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


def test_planner_retries_after_validation_error(monkeypatch) -> None:
    good = {
        "objective": "Segment counts",
        "plan": [
            {
                "id": 1,
                "purpose": "Count by segment",
                "type": "sql",
                "query": "SELECT 1 AS value",
                "output_alias": "counts",
            }
        ],
        "max_steps": 3,
        "metric": "",
        "metric_direction": "",
    }
    bad = {
        "objective": "Too many",
        "plan": good["plan"] * 4,
        "max_steps": 3,
        "metric": "",
        "metric_direction": "",
    }

    class FlakyPlannerLLM:
        def __init__(self) -> None:
            self.calls = 0

        def generate_json(self, prompt: str, schema=None):  # noqa: ANN001, ARG002
            self.calls += 1
            if self.calls == 1:
                return bad
            return good

    stub = FlakyPlannerLLM()
    monkeypatch.setattr("app.agent.planner.get_llm_client", lambda: stub)

    state = create_initial_state("Compare segments")
    state["dataset_context"] = {"reference_date": "2017-12-31", "relations": [], "views": []}
    state = plan_compiled_query(state)

    assert stub.calls == 2
    assert state["compiled_plan"] is not None
    assert len(state["compiled_plan"]["plan"]) == 1


def test_semantic_context_exposes_normalized_manifest() -> None:
    asset = ingest_source("pipeline.csv", b"owner,pipeline_velocity_days\nAda,10\nBen,14\n")
    manifest = get_semantic_context().schema_manifest

    assert manifest["dialect"] == "duckdb"
    assert manifest["relations"]
    relation = next(relation for relation in manifest["relations"] if relation["name"] == asset.primaryRelationName)
    assert relation["columns"]
    assert relation["identifier_columns"]
    assert relation["grain"]


def test_planner_retries_after_sql_preflight_failure(monkeypatch) -> None:
    asset = ingest_source("pipeline.csv", b"owner,pipeline_velocity_days\nAda,10\nBen,14\n")
    relation_name = asset.primaryRelationName
    bad = {
        "objective": "Analyze by sales agent",
        "plan": [
            {
                "id": 1,
                "purpose": "Break out velocity by agent",
                "type": "sql",
                "query": f"SELECT sales_agent, AVG(pipeline_velocity_days) AS avg_velocity_days FROM {relation_name} GROUP BY sales_agent",
                "output_alias": "velocity_by_agent",
            }
        ],
        "max_steps": 3,
        "metric": "pipeline_velocity_days",
        "metric_direction": "lower_is_better",
    }
    good = {
        "objective": "Analyze by owner",
        "plan": [
            {
                "id": 1,
                "purpose": "Break out velocity by owner",
                "type": "sql",
                "query": f"SELECT owner, AVG(pipeline_velocity_days) AS avg_velocity_days FROM {relation_name} GROUP BY owner",
                "output_alias": "velocity_by_owner",
            }
        ],
        "max_steps": 3,
        "metric": "pipeline_velocity_days",
        "metric_direction": "lower_is_better",
    }

    class FlakyPlannerLLM:
        def __init__(self) -> None:
            self.calls = 0
            self.prompts: list[str] = []

        def generate_json(self, prompt: str, schema=None):  # noqa: ANN001, ARG002
            self.calls += 1
            self.prompts.append(prompt)
            if self.calls == 1:
                return bad
            return good

    stub = FlakyPlannerLLM()
    monkeypatch.setattr("app.agent.planner.get_llm_client", lambda: stub)

    state = create_initial_state("Why did pipeline velocity drop this week by sales agent?")
    state["dataset_context"] = get_semantic_context([asset.id]).schema_manifest
    state = plan_compiled_query(state)

    assert stub.calls == 2
    assert "failed SQL preflight validation" in stub.prompts[1]
    assert state["compiled_plan"] is not None
    assert "owner" in state["compiled_plan"]["plan"][0]["query"]
