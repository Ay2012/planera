"""Blob storage for raw uploaded files."""

from __future__ import annotations

from pathlib import Path

from app.config import get_settings


class LocalUploadBlobStore:
    """Persist raw uploads under a stable per-user filesystem path."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or get_settings().upload_storage_dir

    def save(self, *, user_id: int, upload_id: str, filename: str, content: bytes) -> Path:
        suffix = Path(filename).suffix.lower()
        upload_dir = self.root / str(user_id) / upload_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        path = upload_dir / f"original{suffix}"
        path.write_bytes(content)
        return path

    def delete(self, storage_path: str | Path) -> None:
        path = Path(storage_path)
        if path.exists():
            path.unlink()
        current = path.parent
        root = self.root.resolve()
        while current.exists() and current != root:
            if any(current.iterdir()):
                break
            current.rmdir()
            current = current.parent
