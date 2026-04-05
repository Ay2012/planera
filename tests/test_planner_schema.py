"""Compiled plan schema and planner retry behavior."""

from app.agent.planner import _build_repair_prompt, _schema_subset_for_question, plan_compiled_query, repair_failed_step
from app.agent.state import create_initial_state
from app.data.semantic_model import get_semantic_context
from app.schemas import CompiledPlan


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
                    "expectation": {
                        "step_category": "follow_up",
                        "comparison_type": "single_result",
                        "expected_grouping_columns": [],
                        "expected_metric_columns": ["value"],
                        "expected_period_column": "",
                        "min_expected_rows": 1,
                        "requires_distinct_periods": False,
                        "preserve_population_from_step_id": None,
                    },
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
        "objective": "Revenue comparison",
        "plan": [
            {
                "id": 1,
                "purpose": "Compare current and previous revenue.",
                "type": "sql",
                "query": "SELECT 'Previous Week' AS period, 10 AS revenue UNION ALL SELECT 'Current Week' AS period, 12 AS revenue",
                "expectation": {
                    "step_category": "premise_check",
                    "comparison_type": "period_comparison",
                    "expected_grouping_columns": [],
                    "expected_metric_columns": ["revenue"],
                    "expected_period_column": "period",
                    "min_expected_rows": 2,
                    "requires_distinct_periods": True,
                    "preserve_population_from_step_id": None,
                },
                "output_alias": "weekly_revenue",
            }
        ],
        "max_steps": 3,
        "metric": "revenue",
        "metric_direction": "higher_is_better",
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

    state = create_initial_state("Why did revenue drop this week?")
    state["dataset_context"] = get_semantic_context().schema_manifest
    state = plan_compiled_query(state)

    assert stub.calls == 2
    assert state["compiled_plan"] is not None
    assert len(state["compiled_plan"]["plan"]) == 1


def test_semantic_context_exposes_normalized_manifest() -> None:
    manifest = get_semantic_context().schema_manifest

    assert manifest["dialect"] == "duckdb"
    assert manifest["relations"]
    assert manifest["relationships"] is not None
    relation = next(relation for relation in manifest["relations"] if relation["name"] == "opportunities_enriched")
    assert relation["columns"]
    assert relation["identifier_columns"]
    assert relation["grain"]
    assert relation["columns"][0]["field_origin"] in {"source_backed", "derived"}


def test_planner_retries_after_sql_preflight_failure(monkeypatch) -> None:
    bad = {
        "objective": "Analyze by sales agent",
        "plan": [
            {
                "id": 1,
                "purpose": "Break out velocity by agent",
                "type": "sql",
                "query": "SELECT sales_agent, AVG(pipeline_velocity_days) AS avg_velocity_days FROM opportunities_enriched GROUP BY sales_agent",
                "expectation": {
                    "step_category": "premise_check",
                    "comparison_type": "period_comparison",
                    "expected_grouping_columns": [],
                    "expected_metric_columns": ["avg_velocity_days"],
                    "expected_period_column": "period",
                    "min_expected_rows": 2,
                    "requires_distinct_periods": True,
                    "preserve_population_from_step_id": None,
                },
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
                "query": "SELECT current_period AS period, AVG(pipeline_velocity_days) AS avg_velocity_days FROM opportunities_enriched GROUP BY current_period",
                "expectation": {
                    "step_category": "premise_check",
                    "comparison_type": "period_comparison",
                    "expected_grouping_columns": [],
                    "expected_metric_columns": ["avg_velocity_days"],
                    "expected_period_column": "period",
                    "min_expected_rows": 2,
                    "requires_distinct_periods": True,
                    "preserve_population_from_step_id": None,
                },
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
    state["dataset_context"] = get_semantic_context().schema_manifest
    state = plan_compiled_query(state)

    assert stub.calls == 2
    assert "failed SQL preflight validation" in stub.prompts[1]
    assert state["compiled_plan"] is not None
    assert "current_period AS period" in state["compiled_plan"]["plan"][0]["query"]


def test_schema_subset_preserves_structural_fields() -> None:
    manifest = get_semantic_context().schema_manifest
    subset = _schema_subset_for_question(manifest, "Why did pipeline velocity drop this week by sales rep and region?")

    relation = next(relation for relation in subset["relations"] if relation["name"] == "opportunities_enriched")
    selected_names = {column["name"] for column in relation["columns"]}

    assert set(relation["identifier_columns"]).issubset(selected_names)
    assert set(relation["time_columns"]).issubset(selected_names)
    assert set(relation["measure_columns"]).issubset(selected_names)


def test_repair_prompt_includes_query_and_expectation_context() -> None:
    state = create_initial_state("Why did revenue drop this week?")
    state["dataset_context"] = get_semantic_context().schema_manifest
    state["compiled_plan"] = {
        "objective": "Compare revenue",
        "plan": [
            {
                "id": 1,
                "purpose": "Compare revenue by period.",
                "type": "sql",
                "query": "SELECT sales_agent, SUM(deal_value) AS revenue FROM opportunities_enriched GROUP BY sales_agent",
                "expectation": {
                    "step_category": "premise_check",
                    "comparison_type": "period_comparison",
                    "expected_grouping_columns": [],
                    "expected_metric_columns": ["revenue"],
                    "expected_period_column": "period",
                    "min_expected_rows": 2,
                    "requires_distinct_periods": True,
                    "preserve_population_from_step_id": None,
                },
                "output_alias": "revenue_by_period",
            }
        ],
    }

    prompt = _build_repair_prompt(state, "1", 'Binder Error: Referenced column "sales_agent" not found')

    assert "Why did revenue drop this week?" in prompt
    assert '"expected_period_column": "period"' in prompt
    assert 'Referenced column "sales_agent" not found' in prompt


def test_repair_rejects_expectation_drift(monkeypatch) -> None:
    class RepairLLM:
        def generate_json(self, prompt: str, schema=None):  # noqa: ANN001, ARG002
            return {
                "repair_action": "replace_step",
                "updated_step": {
                    "id": 1,
                    "purpose": "Compare revenue by period.",
                    "type": "sql",
                    "query": "SELECT current_period AS period, SUM(deal_value) AS revenue FROM opportunities_enriched GROUP BY current_period",
                    "expectation": {
                        "step_category": "breakdown",
                        "comparison_type": "grouped_breakdown",
                        "expected_grouping_columns": ["segment"],
                        "expected_metric_columns": ["revenue"],
                        "expected_period_column": "",
                        "min_expected_rows": 1,
                        "requires_distinct_periods": False,
                        "preserve_population_from_step_id": None,
                    },
                    "output_alias": "revenue_by_period",
                },
            }

    monkeypatch.setattr("app.agent.planner.get_llm_client", lambda: RepairLLM())
    state = create_initial_state("Why did revenue drop this week?")
    state["dataset_context"] = get_semantic_context().schema_manifest
    state["compiled_plan"] = {
        "objective": "Compare revenue",
        "plan": [
            {
                "id": 1,
                "purpose": "Compare revenue by period.",
                "type": "sql",
                "query": "SELECT sales_agent, SUM(deal_value) AS revenue FROM opportunities_enriched GROUP BY sales_agent",
                "expectation": {
                    "step_category": "premise_check",
                    "comparison_type": "period_comparison",
                    "expected_grouping_columns": [],
                    "expected_metric_columns": ["revenue"],
                    "expected_period_column": "period",
                    "min_expected_rows": 2,
                    "requires_distinct_periods": True,
                    "preserve_population_from_step_id": None,
                },
                "output_alias": "revenue_by_period",
            }
        ],
    }

    try:
        repair_failed_step(state, "1", 'Binder Error: Referenced column "sales_agent" not found')
    except ValueError as exc:
        assert "changed the original step expectation" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Repair should have rejected expectation drift.")


def test_repair_rejects_premise_check_that_drops_required_metric(monkeypatch) -> None:
    class RepairLLM:
        def generate_json(self, prompt: str, schema=None):  # noqa: ANN001, ARG002
            return {
                "repair_action": "replace_step",
                "updated_step": {
                    "id": 1,
                    "purpose": "Compare velocity by period.",
                    "type": "sql",
                    "query": "SELECT current_period AS period FROM opportunities_enriched LIMIT 1",
                    "expectation": {
                        "step_category": "premise_check",
                        "comparison_type": "period_comparison",
                        "expected_grouping_columns": [],
                        "expected_metric_columns": ["avg_pipeline_velocity"],
                        "expected_period_column": "period",
                        "min_expected_rows": 2,
                        "requires_distinct_periods": True,
                        "preserve_population_from_step_id": None,
                    },
                    "output_alias": "velocity_by_period",
                },
            }

    monkeypatch.setattr("app.agent.planner.get_llm_client", lambda: RepairLLM())
    state = create_initial_state("Why did pipeline velocity drop this week?")
    state["dataset_context"] = get_semantic_context().schema_manifest
    state["compiled_plan"] = {
        "objective": "Compare velocity",
        "plan": [
            {
                "id": 1,
                "purpose": "Compare velocity by period.",
                "type": "sql",
                "query": "SELECT current_period AS period, AVG(pipeline_velocity_days) AS avg_pipeline_velocity_days FROM opportunities_enriched GROUP BY current_period",
                "expectation": {
                    "step_category": "premise_check",
                    "comparison_type": "period_comparison",
                    "expected_grouping_columns": [],
                    "expected_metric_columns": ["avg_pipeline_velocity_days"],
                    "expected_period_column": "period",
                    "min_expected_rows": 2,
                    "requires_distinct_periods": True,
                    "preserve_population_from_step_id": None,
                },
                "output_alias": "velocity_by_period",
            }
        ],
    }

    try:
        repair_failed_step(state, "1", "Binder error")
    except ValueError as exc:
        assert "did not preserve the original analytical intent" in str(exc)
        assert "missing expected columns" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Repair should have been rejected when it dropped the required metric.")
