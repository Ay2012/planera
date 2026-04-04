"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth_routes import router as auth_router
from app.api.chat_routes import router as chat_router
from app.api.routes import router
from app.config import get_settings
from app.utils.logging import configure_logging


settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Create database tables on startup (SQLite file demo; no Alembic in this phase)."""

    from app.db.base import Base
    from app.db.session import get_engine
    from app.models import Conversation, InspectionSnapshot, Message, User  # noqa: F401

    Base.metadata.create_all(bind=get_engine())
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Natural-language analytics copilot for GTM teams.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(router)
