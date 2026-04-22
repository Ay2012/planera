"""Gemini client wrapper for planning and synthesis."""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any, TypeVar

from google import genai
from pydantic import BaseModel

from app.config import get_settings
from app.llm.json_response import validate_structured_output
from app.utils.logging import get_logger

SchemaT = TypeVar("SchemaT", bound=BaseModel)

logger = get_logger(__name__)

# Shared across all GeminiClient instances and requests (planner, query writer, etc.).
_rate_state_lock = threading.Lock()
_request_times: deque[float] = deque()


def _acquire_gemini_request_slot() -> None:
    """Block until a generate_content call is allowed (sliding window over the free-tier RPM)."""

    settings = get_settings()
    max_n = settings.gemini_max_requests_per_minute
    if max_n <= 0:
        return
    window = max(settings.gemini_rate_limit_window_seconds, 0.1)

    while True:
        wait_s = 0.0
        with _rate_state_lock:
            now = time.monotonic()
            while _request_times and now - _request_times[0] >= window:
                _request_times.popleft()
            if len(_request_times) < max_n:
                _request_times.append(now)
                return
            wait_s = max(0.0, window - (now - _request_times[0]) + 0.05)
        if wait_s > 0.5:
            logger.info(
                "Throttling Gemini calls: waiting %.1fs to respect max %d requests / %.0fs (RPM limit).",
                wait_s,
                max_n,
                window,
            )
        time.sleep(wait_s if wait_s > 0 else 0.01)


def _json_schema_for_gemini_structured_output(model: type[BaseModel]) -> dict[str, Any]:
    """Build a JSON Schema that Gemini accepts.

    Pydantic's default schema for ``extra="forbid"`` includes ``additionalProperties: false`` and
    similar keywords. The Gemini API rejects those; we still validate with Pydantic after the call.
    """
    return _strip_gemini_incompatible_json_schema_keywords(model.model_json_schema())


def _strip_gemini_incompatible_json_schema_keywords(value: object) -> Any:
    if isinstance(value, dict):
        return {
            k: _strip_gemini_incompatible_json_schema_keywords(v)
            for k, v in value.items()
            if k
            not in (
                "additionalProperties",
                "unevaluatedProperties",  # OpenAPI / draft 2020-12 style
            )
        }
    if isinstance(value, list):
        return [_strip_gemini_incompatible_json_schema_keywords(v) for v in value]
    return value


class GeminiClient:
    """Thin wrapper around the Gemini API."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required for the agentic workflow.")
        self.model = settings.gemini_model
        self.client = genai.Client(api_key=settings.gemini_api_key)

    def generate_json(self, prompt: str, schema: type[SchemaT]) -> SchemaT:
        """Generate schema-constrained JSON and return a validated model."""

        _acquire_gemini_request_slot()
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_json_schema": _json_schema_for_gemini_structured_output(schema),
            },
        )
        text = response.text or ""
        return validate_structured_output(text, schema=schema, source="gemini")

    def generate_text(self, prompt: str) -> str:
        """Generate free text for final user-facing output."""

        _acquire_gemini_request_slot()
        response = self.client.models.generate_content(model=self.model, contents=prompt)
        return (response.text or "").strip()
