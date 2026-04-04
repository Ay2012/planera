"""SQLite engine and session factory (lazy init so tests can override settings first)."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

_engine = None
_session_factory: sessionmaker[Session] | None = None


def reset_engine_and_session() -> None:
    """Dispose the engine and clear factories (used by tests after changing DB path)."""

    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            f"sqlite:///{settings.database_path}",
            connect_args={"check_same_thread": False},
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _session_factory


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: one request-scoped session."""

    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()
