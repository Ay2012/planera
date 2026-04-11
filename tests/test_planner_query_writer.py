"""Planner and query-writer behavior tests for the staged workflow implementation."""

from __future__ import annotations

from app.agent.planner import _schema_subset_for_question, plan_analysis, replan_analysis
from app.agent.query_writer import write_step_query
from app.agent.state import create_initial_state
from app.data.registry import clear_source_registry, ingest_source
from app.data.semantic_model import clear_semantic_context_cache, get_semantic_context


def test_schema_subset_prefers_relevant_uploaded_relation(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("REGISTRY_PATH", str(tmp_path / "planner_subset.duckdb"))
    clear_source_registry()
    clear_semantic_context_cache()
    try:
        ingest_source("inventory.csv", b"sku,stock\nA1,10\nB2,3\n")
        invoices = ingest_source("invoices.csv", b"invoice_id,invoice_amount,status\ni1,100,paid\ni2,250,due\n")
        ingest_source("campaigns.csv", b"campaign,spend\nspring,1200\nsummer,950\n")

        manifest = get_semantic_context().schema_manifest
        subset = _schema_subset_for_question(manifest, "Which invoice amount is highest?")
    finally:
        clear_source_registry()
        clear_semantic_context_cache()

    assert any(relation["name"] == invoices.primaryRelationName for relation in subset["relations"])


def test_plan_analysis_stores_full_non_sql_plan(monkeypatch) -> None:
    class FakePlannerLLM:
        def generate_json(self, prompt: str, schema=None):  # noqa: ANN001, ARG002
            assert "Do not write SQL" in prompt
            return {
                "objective": "Answer the question with two bounded steps.",
                "can_answer_fully": True,
                "unsupported_requirements": [],
                "steps": [
                    {
                        "id": 1,
                        "purpose": "Summarize velocity by owner.",
                        "depends_on": [],
                        "output_alias": "velocity_by_owner",
                        "relations": ["pipeline_source_1234"],
                        "required_columns": ["pipeline_source_1234.owner", "pipeline_source_1234.pipeline_velocity_days"],
                        "expected_output": "A grouped table by owner.",
                        "allow_empty_result": False,
                    },
                    {
                        "id": 2,
                        "purpose": "Identify the slowest owners from the summary.",
                        "depends_on": [1],
                        "output_alias": "slowest_owners",
                        "relations": ["velocity_by_owner"],
                        "required_columns": ["velocity_by_owner.owner", "velocity_by_owner.avg_velocity_days"],
                        "expected_output": "A ranked subset for the final answer.",
                        "allow_empty_result": False,
                    },
                ],
                "max_steps": 3,
                "metric": "pipeline_velocity_days",
                "metric_direction": "lower_is_better",
            }

    monkeypatch.setattr("app.agent.planner.get_llm_client", lambda: FakePlannerLLM())

    state = create_initial_state("Why is velocity worse for some owners?")
    state["dataset_context"] = {
        "reference_date": "2026-04-10",
        "source": "source_registry",
        "dialect": "duckdb",
        "relations": [
            {
                "name": "pipeline_source_1234",
                "source_id": "source_1234",
                "source_name": "pipeline.csv",
                "is_primary": True,
                "row_count": 20,
                "grain": "One row per opportunity",
                "identifier_columns": ["record_id"],
                "time_columns": [],
                "measure_columns": ["pipeline_velocity_days"],
                "dimension_columns": ["owner"],
                "join_keys": [],
                "semantic_mappings": [],
                "columns": [
                    {"name": "owner", "dtype": "VARCHAR", "type_family": "string", "nullable": False, "semantic_hints": ["owner"]},
                    {
                        "name": "pipeline_velocity_days",
                        "dtype": "DOUBLE",
                        "type_family": "number",
                        "nullable": True,
                        "semantic_hints": ["pipeline velocity"],
                    },
                ],
            }
        ],
    }

    state = plan_analysis(state)

    assert state["workflow_status"] == "planned"
    assert state["current_plan"] is not None
    assert state["current_plan"]["steps"][0]["output_alias"] == "velocity_by_owner"
    assert "sql" not in state["current_plan"]["steps"][0]


def test_plan_analysis_preserves_unsupported_requirements(monkeypatch) -> None:
    class FakePlannerLLM:
        def generate_json(self, prompt: str, schema=None):  # noqa: ANN001, ARG002
            return {
                "objective": "Answer the supported part of the question.",
                "can_answer_fully": False,
                "unsupported_requirements": [
                    {
                        "type": "relationship",
                        "description": "A relationship between customers and invoices is not available.",
                        "relation": "customers_source_1234",
                    }
                ],
                "steps": [],
                "max_steps": 3,
                "metric": "",
                "metric_direction": "",
            }

    monkeypatch.setattr("app.agent.planner.get_llm_client", lambda: FakePlannerLLM())

    state = create_initial_state("Which customers have the highest invoice amount?")
    state["dataset_context"] = {"reference_date": "", "source": "", "dialect": "duckdb", "relations": []}
    state = plan_analysis(state)

    assert state["current_plan"]["can_answer_fully"] is False
    assert state["current_plan"]["unsupported_requirements"][0]["type"] == "relationship"


def test_query_writer_emits_one_query_for_current_step(monkeypatch) -> None:
    class FakeQueryWriterLLM:
        def generate_json(self, prompt: str, schema=None):  # noqa: ANN001, ARG002
            assert "exactly one DuckDB SQL query" in prompt
            return {
                "step_id": 1,
                "sql": "SELECT owner, AVG(pipeline_velocity_days) AS avg_velocity_days FROM pipeline_source_1234 GROUP BY owner",
                "explanation": "Aggregates velocity by owner for the first step.",
            }

    monkeypatch.setattr("app.agent.query_writer.get_llm_client", lambda: FakeQueryWriterLLM())

    state = create_initial_state("Why is velocity worse for some owners?")
    state["schema_context_summary"] = {"reference_date": "", "source": "", "dialect": "duckdb", "relations": []}
    state["current_plan"] = {
        "steps": [
            {
                "id": 1,
                "purpose": "Summarize velocity by owner.",
                "depends_on": [],
                "output_alias": "velocity_by_owner",
                "relations": ["pipeline_source_1234"],
                "required_columns": ["pipeline_source_1234.owner", "pipeline_source_1234.pipeline_velocity_days"],
                "expected_output": "A grouped table by owner.",
                "allow_empty_result": False,
            }
        ]
    }

    state = write_step_query(state)

    assert state["generated_query"]["sql"].startswith("SELECT owner")
    assert state["step_queries"]["1"] == [state["generated_query"]["sql"]]


def test_replan_prompt_includes_failure_summary(monkeypatch) -> None:
    captured: dict[str, str] = {}

    class FakePlannerLLM:
        def generate_json(self, prompt: str, schema=None):  # noqa: ANN001, ARG002
            captured["prompt"] = prompt
            return {
                "objective": "Try a safer fallback plan.",
                "can_answer_fully": False,
                "unsupported_requirements": [],
                "steps": [],
                "max_steps": 3,
                "metric": "",
                "metric_direction": "",
            }

    monkeypatch.setattr("app.agent.planner.get_llm_client", lambda: FakePlannerLLM())

    state = create_initial_state("Why is velocity worse for some owners?")
    state["dataset_context"] = {"reference_date": "", "source": "", "dialect": "duckdb", "relations": []}
    state["current_plan"] = {"objective": "Old plan", "steps": []}
    state["failure_summary"] = "Required column not present in schema/context."

    replan_analysis(state)

    assert "Required column not present in schema/context." in captured["prompt"]
