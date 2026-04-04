"""Tests for deterministic analysis evidence, approved claims, and rendering validation."""

from __future__ import annotations

import pytest

from app.agent.analysis_grounding import build_analysis_evidence, build_approved_claims, validate_rendered_analysis
from app.agent.state import create_initial_state
from app.schemas import AnalysisRenderResponse, ApprovedClaim, EvidenceValue


def test_build_approved_claims_marks_contradicted_premise() -> None:
    state = create_initial_state("Why did pipeline velocity drop this week?")
    state["metric"] = "avg_pipeline_velocity_days"
    state["compiled_plan"] = {"metric_direction": "lower_is_better"}
    state["executed_steps"] = [
        {
            "id": "1",
            "purpose": "Compare weekly metrics",
            "status": "success",
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
    assert "does not support a deterioration premise" in claims[0].statement


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
