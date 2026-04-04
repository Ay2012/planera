"""API routes for GTM Analytics Copilot."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.workspace import get_inspection, profile_upload
from app.auth.deps import get_current_user_optional
from app.config import get_settings
from app.db.session import get_db
from app.models.conversation import Conversation
from app.models.inspection_snapshot import InspectionSnapshot
from app.models.user import User
from app.schemas import AnalyzeRequest, AnalyzeResponse, HealthResponse, InspectionData, InspectionResponse, SampleQuestionsResponse, UploadResponse
from app.services.analysis_run import run_stored_analysis
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
def inspection_details(
    inspection_id: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> InspectionResponse:
    """Return a stored inspection (database snapshot for chat history, else in-memory from /analyze)."""

    row = db.get(InspectionSnapshot, inspection_id)
    if row is not None:
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Authentication required to view this inspection."},
                headers={"WWW-Authenticate": "Bearer"},
            )
        conv = db.get(Conversation, row.conversation_id)
        if conv is None or conv.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"message": "Not allowed to view this inspection."},
            )
        inspection = InspectionData.model_validate(row.payload_json)
        return InspectionResponse(inspection=inspection, fallback=False)

    inspection = get_inspection(inspection_id)
    if inspection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": "Inspection not found."})
    return InspectionResponse(inspection=inspection, fallback=False)


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """Execute the analytics workflow for a user query."""

    try:
        return run_stored_analysis(request.query).response
    except Exception as exc:  # pragma: no cover - defensive API fallback
        logger.exception("Analyze request failed", extra={"query": request.query})
        settings = get_settings()
        detail: dict[str, str] = {
            "message": "The analysis could not complete successfully. Inspect the server logs and retry.",
        }
        if settings.app_env.lower() != "production":
            detail["error"] = str(exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail) from exc
