"""Graph-node regressions for execution status transitions."""

from app.agent.graph import execute_plan_node
from app.agent.state import create_initial_state


def test_execute_plan_node_keeps_partial_execution_when_repaired_step_is_still_invalid(monkeypatch) -> None:
    state = create_initial_state("Why did revenue drop this week?")
    state["workflow_status"] = "ready_to_execute"
    state["compiled_plan"] = {
        "objective": "Investigate revenue change",
        "plan": [
            {
                "id": 1,
                "purpose": "Compare weekly revenue.",
                "type": "sql",
                "query": "SELECT 'Previous Week' AS period, 100 AS revenue UNION ALL SELECT 'Current Week' AS period, 120 AS revenue",
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
            },
            {
                "id": 2,
                "purpose": "Break revenue out by owner.",
                "type": "sql",
                "query": "SELECT owner, SUM(revenue) AS revenue FROM opportunities_enriched GROUP BY owner",
                "expectation": {
                    "step_category": "breakdown",
                    "comparison_type": "grouped_breakdown",
                    "expected_grouping_columns": ["owner"],
                    "expected_metric_columns": ["revenue"],
                    "expected_period_column": "",
                    "min_expected_rows": 1,
                    "requires_distinct_periods": False,
                    "preserve_population_from_step_id": 1,
                },
                "output_alias": "owner_revenue",
            },
        ],
    }

    def fake_execute_plan(local_state, plan):  # noqa: ANN001
        local_state["executed_steps"].append(
            {
                "id": "1",
                "purpose": "Compare weekly revenue.",
                "status": "success",
                "validation_status": "valid",
                "output_alias": "weekly_revenue",
                "artifact": {
                    "alias": "weekly_revenue",
                    "columns": ["period", "revenue"],
                    "preview_rows": [
                        {"period": "Previous Week", "revenue": 100},
                        {"period": "Current Week", "revenue": 120},
                    ],
                },
            }
        )
        local_state["executed_steps"].append(
            {
                "id": "2",
                "purpose": "Break revenue out by owner.",
                "status": "invalid",
                "validation_status": "invalid",
                "validation_reason": "The result is missing expected columns: owner.",
                "output_alias": "owner_revenue",
                "artifact": None,
            }
        )
        return {"status": "invalid", "failed_step_id": "2", "error": "The result is missing expected columns: owner."}

    def fake_repair(local_state, failed_step_id, error_message):  # noqa: ANN001
        assert failed_step_id == "2"
        assert "owner" in error_message
        return local_state

    def fake_execute_single(local_state, step_row, attempt):  # noqa: ANN001
        assert attempt == 2
        assert str(step_row["id"]) == "2"
        local_state["executed_steps"].append(
            {
                "id": "2",
                "purpose": "Break revenue out by owner.",
                "status": "invalid",
                "attempt": 2,
                "validation_status": "invalid",
                "validation_reason": "The workflow could not validate a reliable grouped result for Break revenue out by owner.",
                "output_alias": "owner_revenue",
                "artifact": None,
            }
        )
        return {
            "status": "invalid",
            "failed_step_id": "2",
            "error": "The workflow could not validate a reliable grouped result for Break revenue out by owner.",
        }

    monkeypatch.setattr("app.agent.graph.execute_plan", fake_execute_plan)
    monkeypatch.setattr("app.agent.graph.repair_failed_step", fake_repair)
    monkeypatch.setattr("app.agent.graph.execute_single_plan_step", fake_execute_single)

    state = execute_plan_node(state)

    assert state["workflow_status"] == "partial_execution"
    assert state["unresolved_step_ids"] == ["2"]
    assert any(step["id"] == "1" and step["status"] == "success" for step in state["executed_steps"])
    assert state["trace"][-1]["status"] == "failed"
