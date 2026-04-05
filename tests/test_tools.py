"""Executor tests for compiled SQL plans."""

from app.agent.executor import execute_plan, execute_single_plan_step
from app.agent.state import create_initial_state
from app.data.semantic_model import get_semantic_context


def test_execute_sql_step_returns_artifact_summary() -> None:
    state = create_initial_state("Compare SMB vs Enterprise performance")
    state["dataset_context"] = get_semantic_context().schema_manifest
    compiled_plan = {
        "objective": "Segment counts",
        "max_steps": 3,
        "plan": [
            {
                "id": 1,
                "purpose": "Get one sample aggregation.",
                "type": "sql",
                "query": "SELECT segment, COUNT(*) AS deals FROM opportunities_enriched GROUP BY segment ORDER BY deals DESC",
                "expectation": {
                    "step_category": "breakdown",
                    "comparison_type": "grouped_breakdown",
                    "expected_grouping_columns": ["segment"],
                    "expected_metric_columns": ["deals"],
                    "expected_period_column": "",
                    "min_expected_rows": 1,
                    "requires_distinct_periods": False,
                    "preserve_population_from_step_id": None,
                },
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
    state = create_initial_state("Why did pipeline velocity drop this week?")
    state["dataset_context"] = get_semantic_context().schema_manifest
    compiled_plan = {
        "objective": "Empty query",
        "max_steps": 3,
        "plan": [
            {
                "id": 1,
                "purpose": "Return no rows.",
                "type": "sql",
                "query": "SELECT 1 AS value WHERE 1=0",
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
                "output_alias": "empty_result",
            }
        ],
    }
    outcome = execute_plan(state, compiled_plan)
    assert outcome["status"] == "invalid"
    assert state["executed_steps"][-1]["status"] == "invalid"


def test_execute_single_plan_step_retry() -> None:
    state = create_initial_state("Test retry")
    state["dataset_context"] = get_semantic_context().schema_manifest
    step = {
        "id": 1,
        "purpose": "Get one row.",
        "type": "sql",
        "query": "SELECT 1 AS value",
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
        "output_alias": "r1",
    }
    out = execute_single_plan_step(state, step, attempt=2)
    assert out["status"] == "success"
    assert state["executed_steps"][-1]["attempt"] == 2


def test_execute_plan_rejects_one_period_comparison() -> None:
    state = create_initial_state("Did revenue change this week?")
    state["dataset_context"] = get_semantic_context().schema_manifest
    compiled_plan = {
        "objective": "Compare one period",
        "max_steps": 3,
        "plan": [
            {
                "id": 1,
                "purpose": "Compare current and previous revenue.",
                "type": "sql",
                "query": "SELECT 'Current Week' AS period, 120 AS revenue",
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
    }

    outcome = execute_plan(state, compiled_plan)

    assert outcome["status"] == "invalid"
    assert state["executed_steps"][-1]["validation_reason"] == "The comparison result did not return at least two comparable periods."


def test_execute_single_step_rejects_wrong_group_shape() -> None:
    state = create_initial_state("Break revenue out by segment")
    state["dataset_context"] = get_semantic_context().schema_manifest
    step = {
        "id": 2,
        "purpose": "Break revenue out by segment.",
        "type": "sql",
        "query": "SELECT stage, COUNT(*) AS deals FROM opportunities_enriched GROUP BY stage",
        "expectation": {
            "step_category": "breakdown",
            "comparison_type": "grouped_breakdown",
            "expected_grouping_columns": ["segment"],
            "expected_metric_columns": ["deals"],
            "expected_period_column": "",
            "min_expected_rows": 1,
            "requires_distinct_periods": False,
            "preserve_population_from_step_id": 1,
        },
        "output_alias": "segment_breakdown",
    }

    outcome = execute_single_plan_step(state, step, attempt=2)

    assert outcome["status"] == "invalid"
    assert "missing expected columns: segment" in state["executed_steps"][-1]["validation_reason"]


def test_execute_single_step_marks_grouped_period_comparison_partial_when_only_some_groups_match() -> None:
    state = create_initial_state("How did revenue differ by manager this week versus last week?")
    state["dataset_context"] = get_semantic_context().schema_manifest
    step = {
        "id": 3,
        "purpose": "Compare revenue by manager across periods.",
        "type": "sql",
        "query": (
            "SELECT * FROM ("
            "SELECT 'Cara Losch' AS manager, 'previous_week' AS period, 100 AS revenue "
            "UNION ALL SELECT 'Cara Losch' AS manager, 'current_week' AS period, 120 AS revenue "
            "UNION ALL SELECT 'Rocco Neubert' AS manager, 'current_week' AS period, 80 AS revenue"
            ")"
        ),
        "expectation": {
            "step_category": "breakdown",
            "comparison_type": "grouped_breakdown",
            "expected_grouping_columns": ["manager"],
            "expected_metric_columns": ["revenue"],
            "expected_period_column": "period",
            "min_expected_rows": 2,
            "requires_distinct_periods": True,
            "preserve_population_from_step_id": 1,
        },
        "output_alias": "manager_revenue",
    }

    outcome = execute_single_plan_step(state, step, attempt=1)

    assert outcome["status"] == "success"
    assert state["executed_steps"][-1]["validation_status"] == "partial"
    assert "Only 1 of 2 groups returned comparable periods." == state["executed_steps"][-1]["validation_reason"]


def test_execute_single_step_accepts_canonical_metric_alias_for_pipeline_velocity_average() -> None:
    state = create_initial_state("Why did pipeline velocity drop this week?")
    state["dataset_context"] = get_semantic_context().schema_manifest
    step = {
        "id": 4,
        "purpose": "Compare average pipeline velocity by period.",
        "type": "sql",
        "query": (
            "SELECT * FROM ("
            "SELECT 'previous_week' AS period, 69.94 AS avg_pipeline_velocity "
            "UNION ALL SELECT 'current_week' AS period, 64.13 AS avg_pipeline_velocity"
            ")"
        ),
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
        "output_alias": "velocity_comparison",
    }

    outcome = execute_single_plan_step(state, step, attempt=1)

    assert outcome["status"] == "success"
    assert state["executed_steps"][-1]["artifact"]["columns"] == ["period", "avg_pipeline_velocity_days"]
    assert state["executed_steps"][-1]["validation_status"] == "valid"


def test_execute_single_step_accepts_period_comparison_when_period_is_listed_as_grouping_column() -> None:
    state = create_initial_state("Why did pipeline velocity drop this week?")
    state["dataset_context"] = get_semantic_context().schema_manifest
    step = {
        "id": 5,
        "purpose": "Premise check: Compare average pipeline_velocity_days for current week vs previous week to confirm pipeline velocity drop",
        "type": "sql",
        "query": (
            "SELECT "
            "CASE WHEN current_period = TRUE THEN 'current_week' "
            "WHEN previous_period = TRUE THEN 'previous_week' END AS period, "
            "AVG(pipeline_velocity_days) AS avg_pipeline_velocity_days "
            "FROM opportunities_enriched "
            "WHERE current_period = TRUE OR previous_period = TRUE "
            "GROUP BY 1 ORDER BY 1"
        ),
        "expectation": {
            "step_category": "premise_check",
            "comparison_type": "period_comparison",
            "expected_grouping_columns": ["period"],
            "expected_metric_columns": ["avg_pipeline_velocity_days"],
            "expected_period_column": "period",
            "min_expected_rows": 2,
            "requires_distinct_periods": True,
            "preserve_population_from_step_id": None,
        },
        "output_alias": "pipeline_velocity_comparison",
    }

    outcome = execute_single_plan_step(state, step, attempt=2)

    assert outcome["status"] == "success"
    assert state["executed_steps"][-1]["validation_status"] == "valid"
    assert state["executed_steps"][-1]["artifact"]["columns"] == ["period", "avg_pipeline_velocity_days"]
