"""Tests for deterministic analysis evidence, approved claims, and rendering validation."""

from __future__ import annotations

import pytest

from app.agent.analysis_grounding import build_analysis_evidence, build_approved_claims, validate_rendered_analysis
from app.agent.state import create_initial_state
from app.schemas import AnalysisRenderResponse, ApprovedClaim, EvidenceValue


def test_build_approved_claims_marks_contradicted_premise() -> None:
    state = create_initial_state("Why did pipeline velocity drop this week?")
    state["compiled_plan"] = {
        "metric": "avg_pipeline_velocity_days",
        "metric_direction": "",
        "plan": [
            {
                "expectation": {
                    "step_category": "premise_check",
                    "comparison_type": "period_comparison",
                    "expected_grouping_columns": [],
                    "expected_metric_columns": ["avg_pipeline_velocity_days"],
                    "expected_period_column": "period",
                    "min_expected_rows": 2,
                    "requires_distinct_periods": True,
                    "preserve_population_from_step_id": None,
                }
            }
        ],
    }
    state["executed_steps"] = [
        {
            "id": "1",
            "purpose": "Compare weekly metrics",
            "status": "success",
            "validation_status": "valid",
            "output_alias": "weekly_pipeline_metrics",
            "artifact": {
                "alias": "weekly_pipeline_metrics",
                "columns": ["period", "avg_pipeline_velocity_days"],
                "preview_rows": [
                    {"period": "Previous Week", "avg_pipeline_velocity_days": 69.9423076923077},
                    {"period": "Current Week", "avg_pipeline_velocity_days": 64.13291139240506},
                ],
            },
        }
    ]

    evidence = build_analysis_evidence(state)
    claims, status = build_approved_claims(evidence)

    assert status == "contradicted_premise"
    assert claims[0].kind == "premise_check"
    assert claims[0].statement.startswith("The premise is not supported.")


def test_validate_rendered_analysis_rejects_changed_entity_name() -> None:
    claim = ApprovedClaim(
        id="claim_manager",
        kind="row_observation",
        statement="For Celia Rouche, current_week_avg_velocity = 64.65.",
        entities=["Celia Rouche"],
        metrics=["current_week_avg_velocity"],
        source_aliases=["regional_manager_velocity"],
        values=[EvidenceValue(label="current_week_avg_velocity", value="64.65")],
    )
    response = AnalysisRenderResponse(
        answer_status="answered",
        analysis_markdown="## Summary\nFor eCelia Rouche, current_week_avg_velocity = 64.65.",
        used_claim_ids=["claim_manager"],
    )

    with pytest.raises(ValueError, match="changed an approved entity name"):
        validate_rendered_analysis(response, [claim], expected_status="answered")


def test_validate_rendered_analysis_rejects_unapproved_numbers() -> None:
    claim = ApprovedClaim(
        id="claim_manager",
        kind="row_observation",
        statement="For Celia Rouche, current_week_avg_velocity = 64.65.",
        entities=["Celia Rouche"],
        metrics=["current_week_avg_velocity"],
        source_aliases=["regional_manager_velocity"],
        values=[EvidenceValue(label="current_week_avg_velocity", value="64.65")],
    )
    response = AnalysisRenderResponse(
        answer_status="answered",
        analysis_markdown="## Summary\nFor Celia Rouche, current_week_avg_velocity = 60.",
        used_claim_ids=["claim_manager"],
    )

    with pytest.raises(ValueError, match="introduced numbers not present"):
        validate_rendered_analysis(response, [claim], expected_status="answered")


def test_build_approved_claims_marks_partial_answer_when_caveats_remain() -> None:
    state = create_initial_state("How did revenue change this week?")
    state["metric"] = "revenue"
    state["compiled_plan"] = {"metric_direction": "higher_is_better"}
    state["executed_steps"] = [
        {
            "id": "1",
            "purpose": "Compare weekly revenue",
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
    ]

    evidence = build_analysis_evidence(state)
    claims, status = build_approved_claims(
        evidence,
        unresolved_steps=[
            {
                "id": "2",
                "purpose": "Break revenue out by owner",
                "status": "invalid",
                "output_alias": "owner_revenue",
            }
        ],
    )

    assert status == "partial_answer"
    assert any(claim.kind == "comparison" for claim in claims)
    assert any(claim.kind == "caveat" for claim in claims)


def test_build_analysis_evidence_normalizes_boolean_period_labels() -> None:
    state = create_initial_state("How did pipeline velocity differ by manager this week versus last week?")
    state["compiled_plan"] = {
        "metric": "avg_pipeline_velocity_days",
        "metric_direction": "lower_is_better",
        "plan": [
            {
                "expectation": {
                    "step_category": "breakdown",
                    "comparison_type": "grouped_breakdown",
                    "expected_grouping_columns": ["manager"],
                    "expected_metric_columns": ["avg_pipeline_velocity_days"],
                    "expected_period_column": "current_period",
                    "min_expected_rows": 2,
                    "requires_distinct_periods": True,
                    "preserve_population_from_step_id": 1,
                }
            }
        ],
    }
    state["executed_steps"] = [
        {
            "id": "2",
            "purpose": "Compare manager velocity by week",
            "status": "success",
            "validation_status": "valid",
            "output_alias": "manager_velocity",
            "expectation": state["compiled_plan"]["plan"][0]["expectation"],
            "artifact": {
                "alias": "manager_velocity",
                "columns": ["manager", "current_period", "avg_pipeline_velocity_days"],
                "preview_rows": [
                    {"manager": "Cara Losch", "current_period": False, "avg_pipeline_velocity_days": 71.09},
                    {"manager": "Cara Losch", "current_period": True, "avg_pipeline_velocity_days": 63.56},
                ],
            },
        }
    ]

    evidence = build_analysis_evidence(state)

    labels = [item.row_label for item in evidence.items]
    assert "Cara Losch | previous_week" in labels
    assert "Cara Losch | current_week" in labels
    assert all("True" not in label and "False" not in label for label in labels)


def test_validate_rendered_analysis_requires_verdict_first_for_contradiction() -> None:
    claim = ApprovedClaim(
        id="claim_premise_check",
        kind="premise_check",
        statement=(
            "The premise is not supported. avg_pipeline_velocity_days was 69.94 for previous_week and 64.13 "
            "for current_week, and lower is better."
        ),
        entities=["previous_week", "current_week"],
        metrics=["avg_pipeline_velocity_days"],
        source_aliases=["weekly_pipeline_metrics"],
        values=[
            EvidenceValue(label="previous_week.avg_pipeline_velocity_days", value="69.94"),
            EvidenceValue(label="current_week.avg_pipeline_velocity_days", value="64.13"),
        ],
    )
    response = AnalysisRenderResponse(
        answer_status="contradicted_premise",
        analysis_markdown=(
            "avg_pipeline_velocity_days was 69.94 for previous_week and 64.13 for current_week.\n"
            "The premise is not supported."
        ),
        used_claim_ids=["claim_premise_check"],
    )

    with pytest.raises(ValueError, match="first sentence"):
        validate_rendered_analysis(response, [claim], expected_status="contradicted_premise")


def test_validate_rendered_analysis_rejects_internal_workflow_leakage() -> None:
    claim = ApprovedClaim(
        id="claim_manager",
        kind="row_observation",
        statement="For Celia Rouche, current_week_avg_velocity = 64.65.",
        entities=["Celia Rouche"],
        metrics=["current_week_avg_velocity"],
        source_aliases=["regional_manager_velocity"],
        values=[EvidenceValue(label="current_week_avg_velocity", value="64.65")],
    )
    response = AnalysisRenderResponse(
        answer_status="answered",
        analysis_markdown="## Summary\nValidator exception review executed steps and trace for raw outputs.",
        used_claim_ids=["claim_manager"],
    )

    with pytest.raises(ValueError, match="internal workflow text"):
        validate_rendered_analysis(response, [claim], expected_status="answered")
