"""Gemini-based synthesis from verified artifacts."""

from __future__ import annotations

import json

from app.agent.state import AnalysisState
from app.llm import get_llm_client


def synthesize_findings(state: AnalysisState) -> AnalysisState:
    """Generate a business summary and root cause from verified evidence."""

    prompt = f"""
You are writing the business explanation for a GTM analytics agent.

Use only the verified evidence and executed step summaries below.
Do not invent numbers.
Return JSON only in this shape:
{{
  "summary": "...",
  "root_cause": "...",
  "recommendation": "..."
}}

User query:
{state["query"]}

Verified evidence:
{json.dumps(state["evidence"], indent=2)}

Executed steps:
{json.dumps(state["executed_steps"], indent=2)}
"""
    result = get_llm_client().generate_json(prompt)
    state["summary"] = result["summary"]
    state["root_cause"] = result["root_cause"]
    state["recommendation"] = result["recommendation"]
    return state
