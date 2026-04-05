"""Persisted inspection payload for chat history (survives process restart)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.conversation import Conversation, Message


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InspectionSnapshot(Base):
    """Full `InspectionData` JSON keyed by public inspection id (e.g. inspect_abc12def)."""

    __tablename__ = "inspection_snapshots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False)
    message_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)

    conversation: Mapped[Conversation] = relationship("Conversation", back_populates="inspection_snapshots")
    message: Mapped[Message] = relationship("Message", back_populates="inspection_snapshot")
