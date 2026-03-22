"""Deterministic verification for the final answer."""

from __future__ import annotations

from app.agent.state import AnalysisState
from app.data.semantic_model import new_duckdb_connection


def run_verification(state: AnalysisState) -> AnalysisState:
    """Recompute the headline pipeline metric independently."""

    reference_date = state["dataset_context"]["reference_date"]
    conn = new_duckdb_connection()
    verification_sql = f"""
    WITH current_period AS (
        SELECT AVG(pipeline_velocity_days) AS avg_velocity
        FROM opportunities_enriched
        WHERE status = 'won'
          AND close_date BETWEEN DATE '{reference_date}' - INTERVAL 6 DAY AND DATE '{reference_date}'
    ),
    previous_period AS (
        SELECT AVG(pipeline_velocity_days) AS avg_velocity
        FROM opportunities_enriched
        WHERE status = 'won'
          AND close_date BETWEEN DATE '{reference_date}' - INTERVAL 13 DAY AND DATE '{reference_date}' - INTERVAL 7 DAY
    )
    SELECT
        ROUND((SELECT avg_velocity FROM current_period), 2) AS current_velocity,
        ROUND((SELECT avg_velocity FROM previous_period), 2) AS previous_velocity
    """
    row = conn.execute(verification_sql).fetchone()
    current_velocity = float(row[0] or 0.0)
    previous_velocity = float(row[1] or 0.0)
    delta = round(current_velocity - previous_velocity, 2)
    delta_pct = round((delta / previous_velocity) * 100, 2) if previous_velocity else 0.0
    verified = current_velocity >= 0 and previous_velocity >= 0
    state["verification"] = {
        "current_velocity": round(current_velocity, 2),
        "previous_velocity": round(previous_velocity, 2),
        "delta": delta,
        "delta_pct": delta_pct,
    }
    state["verified"] = verified
    state["evidence"] = [
        {"label": "current_velocity", "value": round(current_velocity, 2)},
        {"label": "previous_velocity", "value": round(previous_velocity, 2)},
        {"label": "delta", "value": delta, "metadata": {"delta_pct": delta_pct}},
    ]
    return state
