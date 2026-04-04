"""Persist full inspection payloads for authenticated chat turns."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.inspection_snapshot import InspectionSnapshot
from app.schemas import InspectionData


def save_inspection_for_assistant_message(
    db: Session,
    *,
    inspection_id: str,
    payload: InspectionData,
    conversation_id: int,
    message_id: int,
) -> None:
    """Store a JSON snapshot of `InspectionData` for later GET /inspections/{id}."""

    snap = InspectionSnapshot(
        id=inspection_id,
        conversation_id=conversation_id,
        message_id=message_id,
        payload_json=payload.model_dump(mode="json"),
    )
    db.add(snap)
