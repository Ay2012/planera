"""Premium Streamlit UI for the GTM Analytics Copilot demo."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
import requests
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
DEFAULT_QUERY = "Why did pipeline velocity drop this week?"
REQUEST_TIMEOUT_SECONDS = 120


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg-1: #f6f7ff;
            --bg-2: #eef4ff;
            --bg-3: #f7f5ff;
            --card-bg: rgba(255, 255, 255, 0.68);
            --card-border: rgba(255, 255, 255, 0.65);
            --card-shadow: 0 18px 60px rgba(70, 88, 144, 0.12);
            --text-1: #162033;
            --text-2: #5d6883;
            --accent-a: #5689ff;
            --accent-b: #8f63ff;
            --accent-c: #67d0ff;
            --success-bg: rgba(32, 188, 117, 0.14);
            --success-text: #0e8a4f;
            --warn-bg: rgba(245, 176, 54, 0.18);
            --warn-text: #9b6400;
            --dark-input: linear-gradient(180deg, rgba(17, 24, 39, 0.96), rgba(12, 18, 31, 0.94));
            --radius-xl: 28px;
            --radius-lg: 22px;
            --radius-md: 18px;
            --line-soft: rgba(112, 132, 186, 0.18);
            --line-strong: rgba(112, 132, 186, 0.44);
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(86, 137, 255, 0.20), transparent 34%),
                radial-gradient(circle at top right, rgba(143, 99, 255, 0.15), transparent 28%),
                linear-gradient(180deg, var(--bg-1) 0%, var(--bg-2) 52%, #f8fbff 100%);
            color: var(--text-1);
        }

        [data-testid="stAppViewContainer"] {
            background: transparent;
        }

        [data-testid="stHeader"] {
            background: transparent;
        }

        section.main > div {
            max-width: 1220px;
            padding-top: 1.4rem;
            padding-bottom: 3.2rem;
        }

        .hero-shell {
            position: relative;
            overflow: hidden;
            padding: 2rem 2.1rem 2.15rem 2.1rem;
            border-radius: 34px;
            background:
                linear-gradient(135deg, rgba(255,255,255,0.82), rgba(255,255,255,0.48)),
                linear-gradient(120deg, rgba(86,137,255,0.12), rgba(143,99,255,0.06));
            border: 1px solid rgba(255, 255, 255, 0.82);
            box-shadow: 0 24px 70px rgba(58, 76, 132, 0.14);
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
            margin-bottom: 0.7rem;
        }

        .hero-shell::after {
            content: "";
            position: absolute;
            inset: auto -60px -90px auto;
            width: 240px;
            height: 240px;
            border-radius: 999px;
            background: radial-gradient(circle, rgba(103, 208, 255, 0.22), transparent 70%);
            pointer-events: none;
        }

        .hero-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.42rem 0.82rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #3656b4;
            background: rgba(86, 137, 255, 0.10);
            border: 1px solid rgba(86, 137, 255, 0.18);
        }

        .hero-title {
            margin: 1rem 0 0.7rem 0;
            font-size: clamp(2.35rem, 5vw, 4rem);
            line-height: 1.04;
            letter-spacing: -0.04em;
            font-weight: 800;
            color: var(--text-1);
        }

        .hero-gradient {
            background: linear-gradient(135deg, var(--accent-a), var(--accent-b));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .hero-subtitle {
            max-width: 780px;
            margin: 0;
            font-size: 1.04rem;
            line-height: 1.75;
            color: var(--text-2);
        }

        .glass-card {
            padding: 1.35rem 1.35rem 1.2rem 1.35rem;
            border-radius: var(--radius-xl);
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            box-shadow: var(--card-shadow);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            height: 100%;
        }

        .glass-card.tight {
            padding: 1rem 1.05rem;
        }

        .workspace-card {
            min-height: 100%;
        }

        .query-card {
            padding: 1.4rem;
            border: 1px solid rgba(122, 146, 214, 0.24);
            box-shadow:
                0 28px 80px rgba(58, 76, 132, 0.16),
                inset 0 1px 0 rgba(255,255,255,0.45);
        }

        .query-frame {
            margin-top: 1.05rem;
            padding: 0.45rem;
            border-radius: 28px;
            background: linear-gradient(135deg, rgba(86, 137, 255, 0.12), rgba(143, 99, 255, 0.1));
            border: 1px solid rgba(118, 143, 214, 0.18);
        }

        .recent-item {
            padding: 0.95rem 1rem 0.9rem 1rem;
            border-radius: 20px;
            background: rgba(255, 255, 255, 0.54);
            border: 1px solid rgba(255, 255, 255, 0.8);
        }

        .recent-query {
            margin: 0 0 0.45rem 0;
            font-size: 1rem;
            font-weight: 700;
            line-height: 1.45;
            color: var(--text-1);
        }

        .recent-summary {
            margin: 0;
            font-size: 0.93rem;
            line-height: 1.65;
            color: var(--text-2);
        }

        .recent-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.3rem 0.6rem;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 0.75rem;
        }

        .recent-badge.verified {
            background: var(--success-bg);
            color: var(--success-text);
        }

        .recent-badge.unverified {
            background: var(--warn-bg);
            color: var(--warn-text);
        }

        .section-kicker {
            margin: 0 0 0.2rem 0;
            font-size: 0.8rem;
            font-weight: 800;
            letter-spacing: 0.10em;
            text-transform: uppercase;
            color: #6a78a3;
        }

        .section-title {
            margin: 0;
            font-size: 1.5rem;
            font-weight: 750;
            letter-spacing: -0.03em;
            color: var(--text-1);
        }

        .workspace-title {
            margin: 0 0 0.75rem 0;
            font-size: 1.15rem;
            font-weight: 760;
            letter-spacing: -0.02em;
            color: var(--text-1);
        }

        .section-copy {
            margin: 0.35rem 0 0 0;
            color: var(--text-2);
            line-height: 1.65;
            font-size: 0.97rem;
        }

        .insight-title {
            margin: 0;
            font-size: 0.86rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: #66749a;
        }

        .insight-body {
            margin: 0.75rem 0 0 0;
            font-size: 1.2rem;
            line-height: 1.7;
            color: var(--text-1);
        }

        .headline-body {
            font-size: 1.45rem;
            font-weight: 700;
            line-height: 1.55;
            letter-spacing: -0.02em;
        }

        .verification-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.5rem 0.85rem;
            border-radius: 999px;
            font-size: 0.85rem;
            font-weight: 800;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            margin-bottom: 0.8rem;
        }

        .verification-pill.verified {
            background: var(--success-bg);
            color: var(--success-text);
            border: 1px solid rgba(32, 188, 117, 0.18);
        }

        .verification-pill.unverified {
            background: var(--warn-bg);
            color: var(--warn-text);
            border: 1px solid rgba(245, 176, 54, 0.2);
        }

        .mini-metric-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.85rem;
            margin-top: 0.35rem;
        }

        .result-stack {
            display: grid;
            gap: 0.95rem;
            margin-top: 1rem;
        }

        .result-divider {
            height: 1px;
            background: linear-gradient(90deg, transparent, var(--line-strong), transparent);
            margin: 0.3rem 0;
        }

        .clean-divider {
            width: 100%;
            height: 1px;
            margin: 1.05rem 0 1.15rem 0;
            background: linear-gradient(90deg, transparent, var(--line-strong), transparent);
            border: 0;
        }

        .subsection-divider {
            width: 100%;
            height: 1px;
            margin: 0.8rem 0 0.95rem 0;
            background: linear-gradient(90deg, transparent, rgba(123, 141, 188, 0.40), transparent);
            border: 0;
        }

        .subsection-label {
            margin: 0;
            font-size: 0.78rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #7280a2;
        }

        .subsection-title {
            margin: 0.22rem 0 0 0;
            font-size: 1.08rem;
            font-weight: 740;
            color: var(--text-1);
            letter-spacing: -0.02em;
        }

        .subsection-copy {
            margin: 0.28rem 0 0 0;
            font-size: 0.93rem;
            line-height: 1.6;
            color: var(--text-2);
        }

        .history-scroll {
            max-height: 390px;
            overflow-y: auto;
            padding-right: 0.35rem;
            margin-top: 0.95rem;
        }

        .history-scroll::-webkit-scrollbar {
            width: 8px;
        }

        .history-scroll::-webkit-scrollbar-thumb {
            background: rgba(128, 145, 188, 0.45);
            border-radius: 999px;
        }

        .history-scroll::-webkit-scrollbar-track {
            background: transparent;
        }

        .mini-metric {
            padding: 1rem;
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.55);
            border: 1px solid rgba(255,255,255,0.72);
        }

        .mini-metric-label {
            font-size: 0.78rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #6a779d;
            margin-bottom: 0.45rem;
        }

        .mini-metric-value {
            font-size: 1.45rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            color: var(--text-1);
        }

        div[data-testid="stTextArea"] textarea {
            background: var(--dark-input) !important;
            color: #f3f7ff !important;
            border: 1px solid rgba(129, 150, 202, 0.34) !important;
            border-radius: 24px !important;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.04), 0 28px 60px rgba(13, 19, 34, 0.24) !important;
            padding: 1.15rem 1.15rem !important;
            font-size: 1.05rem !important;
            line-height: 1.7 !important;
            min-height: 240px !important;
        }

        div[data-testid="stTextArea"] textarea::placeholder {
            color: rgba(232, 238, 255, 0.55) !important;
        }

        div[data-testid="stTextArea"] textarea:focus {
            border-color: rgba(132, 153, 255, 0.5) !important;
            box-shadow:
                0 0 0 4px rgba(115, 92, 255, 0.12),
                inset 0 1px 0 rgba(255,255,255,0.04),
                0 28px 60px rgba(13, 19, 34, 0.26) !important;
        }

        div[data-testid="stButton"] > button {
            width: 100%;
            min-height: 56px;
            border: none;
            border-radius: 999px;
            color: white;
            font-size: 1rem;
            font-weight: 800;
            letter-spacing: 0.01em;
            background: linear-gradient(135deg, #4c8cff 0%, #735cff 100%);
            box-shadow: 0 22px 42px rgba(92, 99, 255, 0.28);
            transition: transform 0.16s ease, box-shadow 0.16s ease, filter 0.16s ease;
        }

        div[data-testid="stButton"] > button:hover {
            transform: translateY(-1px);
            filter: brightness(1.04);
            box-shadow: 0 26px 46px rgba(92, 99, 255, 0.34);
        }

        div[data-testid="stButton"] > button:focus {
            outline: none;
            box-shadow: 0 0 0 4px rgba(115, 92, 255, 0.16), 0 26px 46px rgba(92, 99, 255, 0.3);
        }

        [data-baseweb="tab-list"] {
            gap: 0.55rem;
            padding: 0.2rem;
            border-radius: 999px;
            background: rgba(255,255,255,0.42);
            border: 1px solid rgba(255,255,255,0.55);
            margin-bottom: 1.15rem;
        }

        [data-baseweb="tab"] {
            border-radius: 999px;
            padding: 0.6rem 1rem;
            height: auto;
            font-weight: 700;
            color: #66749a;
        }

        [data-baseweb="tab"][aria-selected="true"] {
            color: white;
            background: linear-gradient(135deg, #5a89ff, #7e61ff);
            box-shadow: 0 10px 24px rgba(95, 104, 255, 0.25);
        }

        .artifact-label {
            font-size: 0.8rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #7280a2;
            margin-bottom: 0.3rem;
        }

        .artifact-title {
            font-size: 1.15rem;
            font-weight: 750;
            color: var(--text-1);
            margin: 0 0 0.2rem 0;
        }

        .artifact-meta {
            font-size: 0.92rem;
            color: var(--text-2);
            line-height: 1.6;
        }

        .status-chip {
            display: inline-flex;
            padding: 0.32rem 0.65rem;
            border-radius: 999px;
            font-size: 0.8rem;
            font-weight: 800;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            margin-bottom: 0.75rem;
        }

        .status-chip.success {
            background: rgba(32, 188, 117, 0.14);
            color: var(--success-text);
        }

        .status-chip.failed {
            background: rgba(255, 102, 102, 0.12);
            color: #b84545;
        }

        .code-shell pre {
            border-radius: 18px !important;
            border: 1px solid rgba(140, 157, 202, 0.2);
            background: linear-gradient(180deg, rgba(14, 20, 34, 0.98), rgba(8, 12, 22, 0.98)) !important;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
        }

        .stDataFrame, div[data-testid="stTable"] {
            border-radius: 18px;
            overflow: hidden;
            border: 1px solid rgba(184, 196, 226, 0.36);
            background: rgba(255,255,255,0.5);
        }

        div[data-testid="stAlert"] {
            border-radius: 18px;
        }

        @media (max-width: 900px) {
            .mini-metric-grid {
                grid-template-columns: 1fr;
            }

            .hero-shell {
                padding: 1.5rem;
                border-radius: 28px;
            }

            .glass-card {
                padding: 1.15rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def analyze_query(query: str) -> dict[str, Any]:
    try:
        response = requests.post(
            f"{API_BASE_URL}/analyze",
            json={"query": query},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return normalize_response_payload(response.json())
    except requests.RequestException as exc:
        return normalize_response_payload(
            {
            "summary": "The backend request failed before the analysis could complete.",
            "root_cause": "The UI could not reach the API or the API returned an error.",
            "recommendation": "Confirm the FastAPI service is running and retry the request.",
            "evidence": [],
            "trace": [],
            "executed_steps": [],
            "verified": False,
            "errors": [
                {
                    "step": "ui_request",
                    "message": str(exc),
                    "recoverable": False,
                    "details": {},
                }
            ],
            }
        )


def ensure_session_state() -> None:
    if "query_input" not in st.session_state:
        st.session_state.query_input = ""
    if "analysis_response" not in st.session_state:
        st.session_state.analysis_response = None
    if "last_query" not in st.session_state:
        st.session_state.last_query = DEFAULT_QUERY
    if "recent_analyses" not in st.session_state:
        st.session_state.recent_analyses = []


def format_value(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        if abs(value) >= 1000:
            return f"{value:,.0f}"
        if value.is_integer():
            return f"{int(value)}"
        return f"{value:,.2f}"
    return str(value)


def truncate_text(value: str, limit: int) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "..."


def normalize_response_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Make the UI resilient to both the old and new backend response contracts."""

    analysis_text = payload.get("analysis")
    summary = payload.get("summary") or analysis_text or "No summary available."

    return {
        "summary": summary,
        "root_cause": payload.get("root_cause") or "See the headline insight and execution trace for the full reasoning path.",
        "recommendation": payload.get("recommendation") or "Review the executed steps and trace to determine the next best action.",
        "evidence": payload.get("evidence", []),
        "trace": payload.get("trace", []),
        "executed_steps": payload.get("executed_steps", []),
        "verified": payload.get("verified", False),
        "errors": payload.get("errors", []),
        "analysis": analysis_text or summary,
    }


def extract_metric(response: dict[str, Any], label: str) -> Any:
    for item in response.get("evidence", []):
        if item.get("label") == label:
            return item.get("value")
    return None


def store_recent_analysis(query: str, response: dict[str, Any]) -> None:
    record = {
        "query": query,
        "summary": response.get("summary", "No summary available."),
        "verified": bool(response.get("verified")),
    }
    history = st.session_state.recent_analyses
    history.insert(0, record)
    st.session_state.recent_analyses = history[:5]


def render_hero() -> None:
    st.markdown(
        """
        <div class="hero-shell">
            <div class="hero-badge">Agentic Analytics Workspace</div>
            <h1 class="hero-title">
                Turn GTM questions into
                <span class="hero-gradient">verified next moves</span>
            </h1>
            <p class="hero-subtitle">
                Ask a revenue question in plain English, watch the agent plan and execute against
                trusted data, and get a crisp explanation with evidence, traceability, and a clear next action.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_clean_divider() -> None:
    st.markdown('<div class="clean-divider"></div>', unsafe_allow_html=True)


def render_query_panel() -> bool:
    st.markdown('<div class="glass-card query-card workspace-card">', unsafe_allow_html=True)
    st.markdown(
        """
        <h2 class="workspace-title">Ask a GTM question</h2>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="query-frame">', unsafe_allow_html=True)
    st.text_area(
        "Ask the copilot",
        key="query_input",
        height=260,
        placeholder="Ask a GTM question, e.g. Why did pipeline velocity drop this week?",
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    analyze_clicked = st.button("Analyze With The Copilot", type="primary", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
    return analyze_clicked


def render_recent_analyses() -> None:
    st.markdown('<div class="glass-card workspace-card">', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="section-kicker">Recent Analyses</div>
        <h2 class="section-title">Last five runs</h2>
        <p class="section-copy">
            A quick scrollable memory of what the copilot analyzed most recently in this session.
        </p>
        """,
        unsafe_allow_html=True,
    )

    history = st.session_state.recent_analyses
    if not history:
        st.markdown(
            """
            <div class="recent-item">
                <p class="recent-query">No analyses yet</p>
                <p class="recent-summary">Run your first GTM question and the latest five outputs will appear here.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="history-scroll">', unsafe_allow_html=True)
        for item in history:
            badge_class = "verified" if item["verified"] else "unverified"
            badge_label = "Verified" if item["verified"] else "Unverified"
            query_snippet = truncate_text(item["query"], 110)
            summary_snippet = truncate_text(item["summary"], 130)
            st.markdown(
                f"""
                <div class="recent-item" style="margin-top: 0.85rem;">
                    <div class="recent-badge {badge_class}">{badge_label}</div>
                    <p class="recent-query">{query_snippet}</p>
                    <p class="recent-summary">{summary_snippet}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_verified_badge(verified: bool) -> str:
    status_class = "verified" if verified else "unverified"
    label = "Verified" if verified else "Unverified"
    icon = "●"
    return f'<div class="verification-pill {status_class}">{icon} {label}</div>'


def render_metric_tiles(response: dict[str, Any]) -> None:
    current_velocity = extract_metric(response, "current_velocity")
    previous_velocity = extract_metric(response, "previous_velocity")
    delta = extract_metric(response, "delta")

    metrics = [
        ("Current velocity", format_value(current_velocity), "days"),
        ("Previous velocity", format_value(previous_velocity), "days"),
        ("Delta", format_value(delta), "days"),
    ]

    st.markdown('<div class="mini-metric-grid">', unsafe_allow_html=True)
    for label, value, suffix in metrics:
        st.markdown(
            f"""
            <div class="mini-metric">
                <div class="mini-metric-label">{label}</div>
                <div class="mini-metric-value">{value} <span style="font-size:0.95rem;color:#7b88aa;font-weight:700;">{suffix}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


def render_results_dashboard(response: dict[str, Any] | None) -> None:
    if not response:
        st.markdown('<div class="glass-card workspace-card">', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="section-kicker">Decision Dashboard</div>
            <h2 class="section-title">Run an analysis to populate the workspace</h2>
            <p class="section-copy">
                Headline insight, root cause, next best action, and verification status will appear here as soon as the first run completes.
            </p>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return

    st.markdown('<div class="glass-card workspace-card">', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="section-kicker">Decision Dashboard</div>
        <h2 class="section-title">Results workspace</h2>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(render_verified_badge(bool(response.get("verified"))), unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="result-stack">
            <div>
                <p class="insight-title">Headline Insight</p>
                <p class="insight-body headline-body">{response.get("summary", "No summary available.")}</p>
            </div>
            <div class="result-divider"></div>
            <div>
                <p class="insight-title">Root Cause</p>
                <p class="insight-body">{response.get("root_cause", "No root-cause narrative available.")}</p>
            </div>
            <div class="result-divider"></div>
            <div>
                <p class="insight-title">Next Best Action</p>
                <p class="insight-body">{response.get("recommendation", "No recommendation available.")}</p>
            </div>
            <div class="result-divider"></div>
            <div>
                <p class="insight-title">Verification Status</p>
                <p class="insight-body">{"Core numbers were independently checked before narration." if response.get("verified") else "The workflow returned findings, but verification did not fully pass."}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_metric_tiles(response)
    st.markdown("</div>", unsafe_allow_html=True)


def render_inline_subsection(label: str, title: str, copy: str | None = None) -> None:
    st.markdown('<div class="subsection-divider"></div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <p class="subsection-label">{label}</p>
        <p class="subsection-title">{title}</p>
        {f'<p class="subsection-copy">{copy}</p>' if copy else ''}
        """,
        unsafe_allow_html=True,
    )


def render_evidence_tab(response: dict[str, Any]) -> None:
    evidence = response.get("evidence", [])
    if not evidence:
        st.info("No structured evidence items were returned for this run.")
    else:
        scalar_items = [item for item in evidence if not isinstance(item.get("value"), (list, dict))]
        if scalar_items:
            columns = st.columns(min(3, len(scalar_items)))
            for column, item in zip(columns, scalar_items[:3]):
                with column:
                    st.markdown(
                        f"""
                        <div class="glass-card tight">
                            <div class="artifact-label">{item.get("label", "evidence").replace("_", " ")}</div>
                            <div class="artifact-title">{format_value(item.get("value"))}</div>
                            <div class="artifact-meta">{item.get("metadata", {}) or "Verified evidence point"}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
        for item in evidence:
            metadata = item.get("metadata", {})
            if metadata.get("kind") == "table" and metadata.get("rows"):
                render_inline_subsection("Breakdown", item.get("label", "table").replace("_", " ").title())
                st.dataframe(pd.DataFrame(metadata["rows"]), use_container_width=True, hide_index=True)

    successful_artifacts = [
        step
        for step in response.get("executed_steps", [])
        if step.get("status") == "success" and step.get("artifact", {}).get("preview_rows")
    ]
    if successful_artifacts:
        render_inline_subsection(
            "Supporting Previews",
            "Executed artifacts worth scanning",
            "Compact previews from successful steps help the evidence feel inspectable and real.",
        )
        for step in successful_artifacts[:3]:
            artifact = step.get("artifact", {})
            with st.expander(f"{artifact.get('alias', step.get('output_alias', 'artifact'))}"):
                st.dataframe(
                    pd.DataFrame(artifact.get("preview_rows", [])),
                    use_container_width=True,
                    hide_index=True,
                )


def render_executed_steps_tab(response: dict[str, Any]) -> None:
    steps = response.get("executed_steps", [])
    if not steps:
        st.info("No execution steps have been recorded yet.")
        return

    for step in steps:
        step_title = f"{step.get('id', 'step')} • {step.get('purpose', 'Execution step')}"
        with st.expander(step_title, expanded=False):
            status_class = "success" if step.get("status") == "success" else "failed"
            st.markdown(
                f'<div class="status-chip {status_class}">{step.get("status", "unknown")}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f"""
                <div class="artifact-label">Output alias</div>
                <div class="artifact-title">{step.get("output_alias", "artifact")}</div>
                <div class="artifact-meta">{step.get("purpose", "")}</div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown('<div class="code-shell">', unsafe_allow_html=True)
            st.code(step.get("code", ""), language=step.get("kind", "sql"))
            st.markdown("</div>", unsafe_allow_html=True)

            artifact = step.get("artifact") or {}
            if artifact:
                meta_columns = st.columns(3)
                meta_columns[0].metric("Rows", artifact.get("row_count", 0))
                meta_columns[1].metric("Columns", len(artifact.get("columns", [])))
                meta_columns[2].metric("Type", artifact.get("artifact_type", "unknown"))
                if artifact.get("preview_rows"):
                    st.dataframe(
                        pd.DataFrame(artifact["preview_rows"]),
                        use_container_width=True,
                        hide_index=True,
                    )

            if step.get("error"):
                st.error(step["error"])


def render_trace_tab(response: dict[str, Any]) -> None:
    trace = response.get("trace", [])
    if not trace:
        st.info("No trace events are available for this run.")
        return

    for event in trace:
        title = f"{event.get('step', 'step')} • {event.get('status', 'unknown')}"
        with st.expander(title, expanded=False):
            details = event.get("details", {})
            if details:
                st.json(details)
            else:
                st.caption("No additional details were attached to this event.")


def render_workflow_notes_tab(response: dict[str, Any]) -> None:
    planner_notes = [
        event.get("details", {})
        for event in response.get("trace", [])
        if event.get("step") == "planner_node" and event.get("status") == "completed"
    ]

    render_inline_subsection(
        "How to read this run",
        "Workflow notes",
        "This panel highlights planner reasoning, loop behavior, and any operational issues without making you sift through the full trace first.",
    )

    if planner_notes:
        for index, note in enumerate(planner_notes, start=1):
            reasoning = note.get("reasoning") or note.get("reasoning_summary") or "Planner note unavailable."
            action = note.get("action", "execute_step")
            st.markdown(
                f"""
                <div class="glass-card tight" style="margin-top: 0.85rem;">
                    <div class="artifact-label">Planner note {index}</div>
                    <div class="artifact-title">{action.replace("_", " ").title()}</div>
                    <div class="artifact-meta">{reasoning}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("No planner notes were captured in the trace.")

    errors = response.get("errors", [])
    if errors:
        render_inline_subsection("Observed issues", "Execution and provider warnings")
        for error in errors:
            st.warning(f"{error.get('step', 'workflow')}: {error.get('message', 'Unknown error')}")


def render_analysis_tabs(response: dict[str, Any] | None) -> None:
    st.markdown(
        """
        <div style="margin-top: 1.2rem;" class="glass-card">
            <div class="section-kicker">Deep Dive</div>
            <h2 class="section-title">Inspect the evidence trail</h2>
            <p class="section-copy">
                Move from conclusion to proof with supporting artifacts, execution steps, trace events, and workflow notes.
            </p>
        """,
        unsafe_allow_html=True,
    )

    tabs = st.tabs(["Evidence", "Executed Steps", "Agent Trace", "Workflow Notes"])
    with tabs[0]:
        if response:
            render_evidence_tab(response)
        else:
            st.info("Evidence will appear after the first analysis run.")
    with tabs[1]:
        if response:
            render_executed_steps_tab(response)
        else:
            st.info("Executed steps will appear after the first analysis run.")
    with tabs[2]:
        if response:
            render_trace_tab(response)
        else:
            st.info("Agent trace events will appear after the first analysis run.")
    with tabs[3]:
        if response:
            render_workflow_notes_tab(response)
        else:
            st.info("Workflow notes will appear after the first analysis run.")

    st.markdown("</div>", unsafe_allow_html=True)


def run_app() -> None:
    st.set_page_config(
        page_title="GTM Analytics Copilot",
        page_icon=":bar_chart:",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    ensure_session_state()
    inject_styles()

    render_hero()
    response = st.session_state.analysis_response
    render_clean_divider()

    workspace_left, workspace_right = st.columns([1.12, 1], gap="large")
    with workspace_left:
        analyze_clicked = render_query_panel()
        if analyze_clicked:
            query = st.session_state.query_input.strip()
            if not query:
                st.warning("Enter a question before running the analysis.")
            else:
                with st.status("Running the GTM analytics workflow...", expanded=True) as status:
                    status.write("Preparing the planner and grounding the query in the active dataset.")
                    status.write("Executing analytical steps and waiting for verified findings.")
                    result = analyze_query(query)
                    status.write("Returning the final decision dashboard to the UI.")
                    if result.get("errors"):
                        status.update(label="Analysis completed with warnings", state="error", expanded=False)
                    else:
                        status.update(label="Analysis completed", state="complete", expanded=False)
                st.session_state.analysis_response = result
                st.session_state.last_query = query
                store_recent_analysis(query, result)
                response = result

        render_clean_divider()
        render_recent_analyses()

    with workspace_right:
        render_results_dashboard(response)

    render_clean_divider()
    render_analysis_tabs(response)


if __name__ == "__main__":
    run_app()
