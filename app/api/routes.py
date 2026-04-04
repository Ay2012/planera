"""API routes for GTM Analytics Copilot."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.agent.graph import run_analysis
from app.api.workspace import get_inspection, profile_upload, store_inspection
from app.config import get_settings
from app.schemas import AnalyzeRequest, AnalyzeResponse, HealthResponse, InspectionResponse, SampleQuestionsResponse, UploadResponse
from app.utils.constants import SAMPLE_QUESTIONS
from app.utils.logging import get_logger


router = APIRouter()
logger = get_logger(__name__)


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Return a simple service health response."""

    settings = get_settings()
    return HealthResponse(status="ok", app_name=settings.app_name)


@router.get("/sample-questions", response_model=SampleQuestionsResponse)
def sample_questions() -> SampleQuestionsResponse:
    """Return curated sample prompts for the UI."""

    return SampleQuestionsResponse(questions=SAMPLE_QUESTIONS)


@router.post("/uploads", response_model=UploadResponse)
async def upload_dataset(file: UploadFile = File(...)) -> UploadResponse:
    """Accept a workspace upload and return a profiled asset summary."""

    contents = await file.read()
    try:
        asset = profile_upload(file.filename or "upload.csv", contents)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"message": str(exc)}) from exc
    return UploadResponse(asset=asset, fallback=False)


@router.get("/inspections/{inspection_id}", response_model=InspectionResponse)
def inspection_details(inspection_id: str) -> InspectionResponse:
    """Return a stored inspection payload for the requested analysis."""

    inspection = get_inspection(inspection_id)
    if inspection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": "Inspection not found."})
    return InspectionResponse(inspection=inspection, fallback=False)


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """Execute the analytics workflow for a user query."""

    try:
        state = run_analysis(request.query)
        base_response = AnalyzeResponse(
            analysis=state["analysis"],
            trace=state.get("trace", []),
            executed_steps=state.get("executed_steps", []),
            errors=state.get("errors", []),
        )
        inspection_id = store_inspection(request.query, base_response)
        return AnalyzeResponse(
            analysis=base_response.analysis,
            trace=base_response.trace,
            executed_steps=base_response.executed_steps,
            errors=base_response.errors,
            inspection_id=inspection_id,
        )
    except Exception as exc:  # pragma: no cover - defensive API fallback
        logger.exception("Analyze request failed", extra={"query": request.query})
        settings = get_settings()
        detail: dict[str, str] = {
            "message": "The analysis could not complete successfully. Inspect the server logs and retry.",
        }
        if settings.app_env.lower() != "production":
            detail["error"] = str(exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail) from exc
