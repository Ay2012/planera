"""Schema-based validation helpers for structured LLM responses."""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.utils.logging import get_logger

logger = get_logger(__name__)

SchemaT = TypeVar("SchemaT", bound=BaseModel)
_MAX_EXCERPT = 500


def _truncate(text: str, max_len: int = _MAX_EXCERPT) -> str:
    if len(text) <= max_len:
        return text
    half = max_len // 2
    return text[:half] + "\n...[truncated]...\n" + text[-half:]


def validate_structured_output(
    payload: str | bytes | bytearray | dict[str, Any] | BaseModel | None,
    *,
    schema: type[SchemaT],
    source: str,
) -> SchemaT:
    """Validate a provider response against a concrete Pydantic schema."""

    if payload is None:
        logger.warning("[%s] Empty structured payload for %s", source, schema.__name__)
        raise ValueError(f"{source}: empty structured response for {schema.__name__}")

    try:
        if isinstance(payload, schema):
            return payload

        if isinstance(payload, BaseModel):
            payload = payload.model_dump()

        if isinstance(payload, (bytes, bytearray)):
            payload = payload.decode("utf-8")

        if isinstance(payload, str):
            stripped = payload.strip()
            if not stripped:
                logger.warning("[%s] Blank structured payload for %s", source, schema.__name__)
                raise ValueError(f"{source}: empty structured response for {schema.__name__}")
            return schema.model_validate_json(stripped)

        return schema.model_validate(payload)
    except ValidationError as exc:
        excerpt = _truncate(str(payload))
        logger.warning(
            "[%s] Structured validation failed for %s: %s; payload=%s",
            source,
            schema.__name__,
            exc.errors(),
            repr(excerpt),
        )
        raise
