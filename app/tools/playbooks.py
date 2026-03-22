"""Rules-based recommendation playbooks."""

from __future__ import annotations

from typing import Any


def _find_top_contributor(evidence: list[dict[str, Any]], dimension: str) -> dict[str, Any] | None:
    for item in evidence:
        if item.get("dimension") == dimension and item.get("top_contributor"):
            return item["top_contributor"]
    return None


def recommend_play(intent: str, metric_name: str, evidence: list[dict[str, Any]]) -> dict[str, Any]:
    """Generate a tactical recommendation from verified evidence."""

    comparison = next((item for item in evidence if item.get("current") and item.get("previous")), None)
    top_segment = _find_top_contributor(evidence, "segment")
    top_stage = _find_top_contributor(evidence, "stage")
    top_owner = _find_top_contributor(evidence, "owner")
    top_plan = _find_top_contributor(evidence, "plan_tier")

    if metric_name == "pipeline_velocity":
        if top_segment and top_stage:
            action = (
                f"Prioritize {top_segment['dimension_value']} deals stalled in {top_stage['dimension_value']} "
                f"and review any records sitting more than 14 days before the next stage handoff."
            )
        elif top_owner:
            action = (
                f"Run a manager review for {top_owner['dimension_value']}'s pipeline and rebalance stalled deals "
                "if capacity is concentrated on one rep."
            )
        else:
            action = "Focus the weekly pipeline review on stale mid-funnel deals and enforce stage-exit criteria."
    else:
        if top_plan:
            action = (
                f"Launch targeted retention outreach for the {top_plan['dimension_value']} tier and review the top churn reasons "
                "before the next renewal window."
            )
        else:
            action = "Prioritize proactive retention outreach for at-risk accounts and tighten renewal check-ins."

    if intent == "recommendation" and comparison and comparison.get("delta", 0) > 0 and metric_name == "pipeline_velocity":
        action += " Start with the oldest open opportunities first to recover cycle time quickly."

    return {
        "intent": intent,
        "metric_name": metric_name,
        "recommendation": action,
    }
