"""Streamlit UI for GTM Analytics Copilot."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
import requests
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def fetch_sample_questions() -> list[str]:
    """Fetch sample prompts from the backend, with a local fallback."""

    fallback = [
        "Why did pipeline velocity drop this week?",
        "Compare SMB vs Enterprise performance",
        "Which segment is underperforming?",
        "What should we do about this drop?",
        "Which deals should we prioritize?",
    ]
    try:
        response = requests.get(f"{API_BASE_URL}/sample-questions", timeout=5)
        response.raise_for_status()
        return response.json()["questions"]
    except Exception:
        return fallback


def analyze_query(query: str) -> dict[str, Any]:
    """Submit a query to the backend API."""

    response = requests.post(f"{API_BASE_URL}/analyze", json={"query": query}, timeout=60)
    response.raise_for_status()
    return response.json()


def render_trace(response: dict[str, Any]) -> None:
    """Render the execution trace with expandable detail."""

    for event in response.get("trace", []):
        status_color = {"completed": "green", "failed": "red", "started": "blue"}.get(event["status"], "gray")
        with st.expander(f"{event['step']} · {event['status']}", expanded=False):
            st.markdown(f":{status_color}[{event['status'].upper()}]")
            st.json(event.get("details", {}))


def render_executed_steps(response: dict[str, Any]) -> None:
    """Render executed SQL/pandas steps and their output previews."""

    for step in response.get("executed_steps", []):
        label = f"{step['id']} · {step['kind']} · {step['status']}"
        with st.expander(label, expanded=False):
            st.markdown(f"**Purpose**: {step['purpose']}")
            st.code(step["code"], language="sql" if step["kind"] == "sql" else "python")
            if step.get("artifact"):
                artifact = step["artifact"]
                st.markdown(f"**Output Alias**: `{step['output_alias']}`")
                st.caption(f"Rows: {artifact.get('row_count', 0)}")
                if artifact.get("preview_rows"):
                    st.dataframe(pd.DataFrame(artifact["preview_rows"]), use_container_width=True, hide_index=True)
            if step.get("error"):
                st.error(step["error"])


def render_errors(response: dict[str, Any]) -> None:
    """Render structured workflow errors when present."""

    errors = response.get("errors", [])
    if not errors:
        return
    st.warning("Some workflow steps reported issues during this run.")
    for error in errors:
        st.code(f"{error['step']}: {error['message']}")


st.set_page_config(page_title="GTM Analytics Copilot", page_icon=":bar_chart:", layout="wide")

st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(251, 191, 36, 0.18), transparent 28%),
            radial-gradient(circle at top right, rgba(14, 116, 144, 0.18), transparent 30%),
            linear-gradient(180deg, #f8fafc 0%, #eff6ff 100%);
        color: #102a43;
        font-family: "IBM Plex Sans", "Avenir Next", sans-serif;
    }
    .hero-card, .panel-card {
        background: rgba(255, 255, 255, 0.88);
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 18px;
        padding: 1.2rem 1.3rem;
        box-shadow: 0 18px 50px rgba(15, 23, 42, 0.08);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

sample_questions = fetch_sample_questions()

if "query" not in st.session_state:
    st.session_state.query = sample_questions[0]
if "result" not in st.session_state:
    st.session_state.result = None

st.markdown(
    """
    <div class="hero-card">
        <h1 style="margin:0;color:#0f172a;">GTM Analytics Copilot</h1>
        <p style="margin:0.5rem 0 0 0;color:#334155;font-size:1.05rem;">
            Ask a GTM business question and get structured analysis backed by executed steps and a full trace.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")

left, right = st.columns([1.6, 1.0])

with left:
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    st.subheader("Query Input")
    selected = st.selectbox("Sample questions", sample_questions, index=sample_questions.index(st.session_state.query) if st.session_state.query in sample_questions else 0)
    if st.button("Use Sample", use_container_width=False):
        st.session_state.query = selected
    st.session_state.query = st.text_area("Business question", value=st.session_state.query, height=110)
    analyze = st.button("Analyze", type="primary", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    st.subheader("What This MVP Does")
    st.markdown(
        """
        - Loads dataset schema (tables, columns, dtypes)
        - LLM plans the next SQL or pandas step
        - Executes against curated views; replans on failure
        - One analysis pass turns results into narrative (markdown)
        """
    )
    st.markdown("</div>", unsafe_allow_html=True)

if analyze and st.session_state.query.strip():
    with st.status("Running planner → execute → analysis...", expanded=True) as status:
        st.write("Loading schema context.")
        st.write("Planning and executing steps.")
        try:
            st.session_state.result = analyze_query(st.session_state.query.strip())
            status.update(label="Analysis complete", state="complete")
        except Exception as exc:
            st.session_state.result = {
                "analysis": "The backend request failed before the analysis could complete.",
                "trace": [],
                "executed_steps": [],
                "errors": [{"step": "ui_request", "message": str(exc), "recoverable": False, "details": {}}],
            }
            status.update(label="Analysis failed", state="error")

result = st.session_state.result

if result:
    st.write("")
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    st.subheader("Analysis")
    st.markdown(result.get("analysis", ""))
    st.markdown("</div>", unsafe_allow_html=True)

    st.write("")
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    st.subheader("Executed Steps")
    render_executed_steps(result)
    st.markdown("</div>", unsafe_allow_html=True)

    st.write("")
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    st.subheader("Agent Trace")
    render_trace(result)
    st.markdown("</div>", unsafe_allow_html=True)

    st.write("")
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    st.subheader("Workflow Notes")
    render_errors(result)
    if not result.get("errors"):
        st.success("No errors recorded for this run.")
    st.markdown("</div>", unsafe_allow_html=True)
