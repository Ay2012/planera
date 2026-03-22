"""Gemini-based recommendation generation."""

from __future__ import annotations

import json

from app.agent.state import AnalysisState
from app.llm import get_llm_client


def build_recommendation(state: AnalysisState) -> AnalysisState:
    """Generate the next-best action from the verified evidence."""

    if state.get("recommendation"):
        return state

    prompt = f"""
You are writing one tactical next-best action for a GTM analytics agent.

Use only the executed-step evidence below.
Keep the recommendation concrete and operational.
Return JSON only:
{{
  "recommendation": "..."
}}

User query:
{state["query"]}

Summary:
{state["summary"]}

Root cause:
{state["root_cause"]}

Evidence:
{json.dumps(state["evidence"], indent=2)}

Executed steps:
{json.dumps(state["executed_steps"], indent=2)}
"""
    result = get_llm_client().generate_json(prompt)
    state["recommendation"] = result["recommendation"]
    return state
