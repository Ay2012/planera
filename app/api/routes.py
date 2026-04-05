"""API routes for GTM Analytics Copilot."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.workspace import get_inspection
from app.auth.deps import get_current_user, get_current_user_optional
from app.config import get_settings
from app.db.session import get_db
from app.models.conversation import Conversation
from app.models.inspection_snapshot import InspectionSnapshot
from app.models.user import User
from app.schemas import AnalyzeRequest, AnalyzeResponse, HealthResponse, InspectionData, InspectionResponse, SampleQuestionsResponse, UploadedAsset, UploadResponse
from app.services.analysis_run import run_stored_analysis
from app.uploads.service import create_user_upload, delete_user_upload, get_authorized_source_ids, list_user_uploads
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


@router.get("/uploads", response_model=list[UploadedAsset])
def list_uploads(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[UploadedAsset]:
    """Return uploads owned by the signed-in user."""

    return list_user_uploads(db, current_user)


@router.post("/uploads", response_model=UploadResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UploadResponse:
    """Accept a workspace upload and return a profiled asset summary."""

    contents = await file.read()
    try:
        asset = create_user_upload(
            db,
            current_user,
            filename=file.filename or "upload.csv",
            content_type=file.content_type,
            content=contents,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"message": str(exc)}) from exc
    return UploadResponse(asset=asset, fallback=False)


@router.delete("/uploads/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_upload(
    source_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Delete one upload owned by the signed-in user."""

    deleted = delete_user_upload(db, current_user, source_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": "Upload not found."})
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/inspections/{inspection_id}", response_model=InspectionResponse)
def inspection_details(
    inspection_id: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> InspectionResponse:
    """Return inspection detail.

    Prefer rows loaded from ``inspection_snapshots`` (written by ``POST /chat``); those require auth.
    Otherwise falls back to the in-memory store populated by a stateless ``POST /analyze`` run in
    the same server process (debug/demo).
    """

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


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    tags=["debug"],
    deprecated=True,
    summary="Stateless analysis (debug / manual testing only)",
    description=(
        "**Not the primary product API.** For normal use, authenticated clients should call "
        "`POST /chat`, which persists conversations, messages, and inspection snapshots.\n\n"
        "This endpoint runs the same analytics pipeline with auth but without conversation/database persistence, "
        "and keeps the inspection payload only in process memory (lost on restart). Use it for "
        "local debugging, Swagger/Postman checks, and quick stateless demos.\n\n"
        "Response shape aligns with the analysis/trace/steps portion of `POST /chat`."
    ),
)
def analyze(
    request: AnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalyzeResponse:
    """Run analytics with auth but without persistence (see OpenAPI ``description`` — prefer ``POST /chat``)."""

    requested_source_ids = list(dict.fromkeys(request.source_ids or []))
    if not requested_source_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Upload and attach at least one CSV or JSON data source before running analysis."},
        )

    valid_source_ids = get_authorized_source_ids(db, current_user, requested_source_ids)
    if len(valid_source_ids) != len(requested_source_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Attach a valid uploaded data source before running analysis."},
        )

    try:
        return run_stored_analysis(request.query, source_ids=valid_source_ids).response
    except Exception as exc:  # pragma: no cover - defensive API fallback
        logger.exception("Analyze request failed", extra={"query": request.query})
        settings = get_settings()
        detail: dict[str, str] = {
            "message": "The analysis could not complete successfully. Inspect the server logs and retry.",
        }
        if settings.app_env.lower() != "production":
            detail["error"] = str(exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail) from exc
