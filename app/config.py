"""Application configuration."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    app_name: str = "GTM Analytics Copilot"
    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    data_dir: Path = Field(default=BASE_DIR / "data")
    registry_path: Path = Field(default=BASE_DIR / "data" / "source_registry.duckdb")
    upload_storage_dir: Path = Field(default=BASE_DIR / "data" / "uploads", alias="UPLOAD_STORAGE_DIR")
    crm_path: Path = Field(default=BASE_DIR / "data" / "crm.csv")
    subscriptions_path: Path = Field(default=BASE_DIR / "data" / "subscriptions.csv")
    crm_dataset_dir: Path = Field(default=BASE_DIR / "data" / "CRM+Sales+Opportunities")
    reference_date: str = "2026-03-21"
    llm_provider: str = Field(default="openai", alias="LLM_PROVIDER")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model: str = "gemini-2.0-flash"
    # Free-tier limits are often 5 RPM; set to 0 to disable throttling (e.g. paid / higher limits).
    gemini_max_requests_per_minute: int = Field(
        default=5,
        alias="GEMINI_MAX_REQUESTS_PER_MINUTE",
    )
    gemini_rate_limit_window_seconds: float = Field(
        default=60.0,
        alias="GEMINI_RATE_LIMIT_WINDOW_SECONDS",
    )
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = "gpt-4.1-mini"
    log_level: str = "INFO"
    cors_allow_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"],
        alias="CORS_ALLOW_ORIGINS",
    )
    # Auth / SQLite (set JWT_SECRET_KEY in any shared or production-like environment)
    database_path: Path = Field(default=BASE_DIR / "planera.db", alias="DATABASE_PATH")
    jwt_secret_key: str = Field(
        default="dev-insecure-jwt-secret-change-me",
        alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=10080, alias="ACCESS_TOKEN_EXPIRE_MINUTES")  # 7 days

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def parse_cors_allow_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""

    return Settings()
