"""API routes for GTM Analytics Copilot."""

from __future__ import annotations

from fastapi import APIRouter

from app.agent.graph import run_analysis
from app.config import get_settings
from app.schemas import AnalyzeRequest, AnalyzeResponse, HealthResponse, SampleQuestionsResponse
from app.utils.constants import SAMPLE_QUESTIONS


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Return a simple service health response."""

    settings = get_settings()
    return HealthResponse(status="ok", app_name=settings.app_name)


@router.get("/sample-questions", response_model=SampleQuestionsResponse)
def sample_questions() -> SampleQuestionsResponse:
    """Return curated sample prompts for the UI."""

    return SampleQuestionsResponse(questions=SAMPLE_QUESTIONS)


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """Execute the analytics workflow for a user query."""

    try:
        state = run_analysis(request.query)
        return AnalyzeResponse(
            summary=state["summary"],
            root_cause=state["root_cause"],
            recommendation=state["recommendation"],
            evidence=state.get("evidence", []),
            trace=state.get("trace", []),
            executed_steps=state.get("executed_steps", []),
            verified=state.get("verified", False),
            errors=state.get("errors", []),
        )
    except Exception as exc:  # pragma: no cover - defensive API fallback
        return AnalyzeResponse(
            summary="The analysis could not complete successfully.",
            root_cause="The workflow failed before verified findings could be produced.",
            recommendation="Inspect the returned error payload, correct the failure, and rerun the analysis.",
            evidence=[],
            trace=[{"step": "api_analyze", "status": "failed", "details": {"message": str(exc)}}],
            executed_steps=[],
            verified=False,
            errors=[{"step": "api_analyze", "message": str(exc), "recoverable": False, "details": {}}],
        )
