"""User-scoped conversation and authenticated chat orchestration.

This module defines the **primary product HTTP API** for analysis turns: ``POST /chat`` persists
messages and inspection snapshots. Stateless ``POST /analyze`` (see ``app.api.routes``) exists only
for debugging and is not a substitute for these routes.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.config import get_settings
from app.db.session import get_db
from app.models.conversation import Conversation, Message
from app.models.user import User
from app.schemas import (
    AnalyzeResponse,
    ChatAssistantMessagePublic,
    ChatSubmitRequest,
    ChatTurnResponse,
    ConversationDetailResponse,
    ConversationPublic,
    ConversationsListResponse,
    ConversationSummary,
    MessagePublic,
)
from app.services.analysis_run import run_stored_analysis
from app.services.inspection_persistence import save_inspection_for_assistant_message
from app.uploads.service import get_authorized_source_ids
from app.utils.logging import get_logger


router = APIRouter(tags=["chat"])
logger = get_logger(__name__)


def _conversation_title_from_query(query: str, max_len: int = 56) -> str:
    compact = " ".join(query.split())
    if len(compact) <= max_len:
        return compact
    return f"{compact[: max_len - 3]}..."


def _preview_text(text: str | None, max_len: int = 120) -> str | None:
    if text is None:
        return None
    single_line = " ".join(text.split())
    if len(single_line) <= max_len:
        return single_line
    return f"{single_line[: max_len - 1]}…"


def _assistant_metadata(result: AnalyzeResponse) -> dict:
    serialized = result.model_dump(mode="json")
    return {
        "trace": serialized["trace"],
        "executed_steps": serialized["executed_steps"],
        "errors": serialized["errors"],
        "inspection_id": serialized["inspection_id"],
    }


@router.get("/conversations", response_model=ConversationsListResponse)
def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationsListResponse:
    last_id_sq = (
        select(Message.conversation_id.label("cid"), func.max(Message.id).label("mid"))
        .group_by(Message.conversation_id)
        .subquery()
    )
    stmt = (
        select(Conversation, Message.content)
        .outerjoin(last_id_sq, last_id_sq.c.cid == Conversation.id)
        .outerjoin(Message, Message.id == last_id_sq.c.mid)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
    )
    rows = db.execute(stmt).all()
    items = [
        ConversationSummary(
            id=conv.id,
            title=conv.title,
            updated_at=conv.updated_at,
            last_message_preview=_preview_text(last_content),
        )
        for conv, last_content in rows
    ]
    return ConversationsListResponse(conversations=items)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationDetailResponse:
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": "Conversation not found."})
    if conv.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"message": "Not allowed to access this conversation."})

    msg_rows = db.execute(
        select(Message)
        .where(Message.conversation_id == conv.id)
        .order_by(Message.created_at.asc(), Message.id.asc())
    ).scalars()

    return ConversationDetailResponse(
        conversation=ConversationPublic.model_validate(conv),
        messages=[MessagePublic.model_validate(m) for m in msg_rows],
    )


@router.post(
    "/chat",
    response_model=ChatTurnResponse,
    summary="Submit one chat turn (primary product path)",
    description=(
        "Authenticated endpoint: saves the user message, runs the analytics workflow, stores the "
        "assistant reply and links an inspection snapshot when present. "
        "Use this for all normal app traffic instead of ``POST /analyze``."
    ),
)
def chat_turn(
    body: ChatSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatTurnResponse:
    now = datetime.now(timezone.utc)
    if body.conversation_id is None:
        conv = Conversation(
            user_id=current_user.id,
            title=_conversation_title_from_query(body.query),
            created_at=now,
            updated_at=now,
        )
        db.add(conv)
        db.flush()
    else:
        conv = db.get(Conversation, body.conversation_id)
        if conv is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": "Conversation not found."})
        if conv.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"message": "Not allowed to access this conversation."},
            )

    user_msg = Message(conversation_id=conv.id, role="user", content=body.query, created_at=now)
    db.add(user_msg)
    db.flush()

    requested_source_ids = list(dict.fromkeys(body.source_ids or []))
    if requested_source_ids:
        valid_source_ids = get_authorized_source_ids(db, current_user, requested_source_ids)
        if len(valid_source_ids) != len(requested_source_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Attach a valid uploaded data source before running analysis."},
            )
    else:
        valid_source_ids = None

    try:
        analysis_run = run_stored_analysis(body.query, source_ids=valid_source_ids)
        analysis_result = analysis_run.response
        inspection_payload = analysis_run.inspection
    except Exception as exc:  # pragma: no cover - defensive API fallback
        db.rollback()
        logger.exception("Chat analyze failed", extra={"query": body.query, "conversation_id": conv.id})
        settings = get_settings()
        detail: dict[str, str] = {
            "message": "The analysis could not complete successfully. Inspect the server logs and retry.",
        }
        if settings.app_env.lower() != "production":
            detail["error"] = str(exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail) from exc

    assistant_meta = _assistant_metadata(analysis_result)
    assistant_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=analysis_result.analysis,
        metadata_json=assistant_meta,
        created_at=datetime.now(timezone.utc),
    )
    db.add(assistant_msg)
    db.flush()
    if analysis_result.inspection_id:
        save_inspection_for_assistant_message(
            db,
            inspection_id=analysis_result.inspection_id,
            payload=inspection_payload,
            conversation_id=conv.id,
            message_id=assistant_msg.id,
        )
    conv.updated_at = assistant_msg.created_at
    db.commit()
    db.refresh(conv)
    db.refresh(assistant_msg)

    return ChatTurnResponse(
        conversation=ConversationPublic.model_validate(conv),
        assistant_message=ChatAssistantMessagePublic(
            id=assistant_msg.id,
            role="assistant",
            content=assistant_msg.content,
            created_at=assistant_msg.created_at,
            status="ready",
            metadata_json=assistant_msg.metadata_json,
        ),
        analysis=analysis_result.analysis,
        trace=analysis_result.trace,
        executed_steps=analysis_result.executed_steps,
        errors=analysis_result.errors,
        inspection_id=analysis_result.inspection_id,
    )
