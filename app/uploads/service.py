"""User-owned upload persistence and authorization helpers."""

from __future__ import annotations

from datetime import timezone
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.registry import delete_source, ingest_source
from app.models.upload import UploadRecord
from app.models.user import User
from app.schemas import UploadedAsset
from app.uploads.storage import LocalUploadBlobStore


def _short_source_id() -> str:
    return f"source_{uuid4().hex[:8]}"


def _to_uploaded_at(value) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _asset_from_record(record: UploadRecord) -> UploadedAsset:
    relation_count = record.relation_count or 0
    summary = None
    if record.rows is not None and record.columns is not None:
        summary = (
            f"Persisted {record.rows} rows across {record.columns} columns"
            f" into {relation_count} relation{'s' if relation_count != 1 else ''}."
        )
        if record.primary_relation_name:
            summary = f"{summary} Primary relation: {record.primary_relation_name}."

    return UploadedAsset(
        id=record.source_id,
        name=record.original_filename,
        type=Path(record.original_filename).suffix.lstrip(".").upper() or "FILE",
        source="Workspace upload",
        sizeLabel=_bytes_to_size(record.size_bytes),
        uploadedAt=_to_uploaded_at(record.created_at),
        status=record.status,  # type: ignore[arg-type]
        rows=record.rows,
        columns=record.columns,
        relationCount=record.relation_count,
        primaryRelationName=record.primary_relation_name,
        summary=summary,
    )


def _bytes_to_size(num_bytes: int) -> str:
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    if num_bytes < 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.1f} MB"
    return f"{num_bytes / (1024 * 1024 * 1024):.1f} GB"


def list_user_uploads(db: Session, user: User) -> list[UploadedAsset]:
    rows = db.execute(
        select(UploadRecord)
        .where(UploadRecord.user_id == user.id)
        .order_by(UploadRecord.created_at.desc(), UploadRecord.source_id.desc())
    ).scalars()
    return [_asset_from_record(row) for row in rows]


def get_authorized_source_ids(db: Session, user: User, source_ids: list[str] | None = None) -> list[str]:
    unique_source_ids = list(dict.fromkeys(source_ids or []))
    if not unique_source_ids:
        return []

    owned_rows = db.execute(
        select(UploadRecord.source_id)
        .where(UploadRecord.user_id == user.id, UploadRecord.source_id.in_(unique_source_ids))
    ).scalars()
    owned_ids = set(owned_rows)
    return [source_id for source_id in unique_source_ids if source_id in owned_ids]


def create_user_upload(
    db: Session,
    user: User,
    *,
    filename: str,
    content_type: str | None,
    content: bytes,
    blob_store: LocalUploadBlobStore | None = None,
) -> UploadedAsset:
    store = blob_store or LocalUploadBlobStore()
    source_id = _short_source_id()
    storage_path = store.save(user_id=user.id, upload_id=source_id, filename=filename, content=content)

    try:
        asset = ingest_source(filename, content, source_id=source_id)
    except Exception:
        store.delete(storage_path)
        raise

    record = UploadRecord(
        source_id=source_id,
        user_id=user.id,
        original_filename=filename,
        storage_path=str(storage_path),
        content_type=content_type or "application/octet-stream",
        size_bytes=len(content),
        content_hash=sha256(content).hexdigest(),
        status=asset.status,
        rows=asset.rows,
        columns=asset.columns,
        relation_count=asset.relationCount,
        primary_relation_name=asset.primaryRelationName,
    )
    db.add(record)

    try:
        db.commit()
    except Exception:
        db.rollback()
        delete_source(source_id)
        store.delete(storage_path)
        raise

    db.refresh(record)
    return _asset_from_record(record)
