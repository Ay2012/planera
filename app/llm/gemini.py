"""Gemini client wrapper for planning and synthesis."""

from __future__ import annotations

from typing import TypeVar

from google import genai
from pydantic import BaseModel

from app.config import get_settings
from app.llm.json_response import validate_structured_output

SchemaT = TypeVar("SchemaT", bound=BaseModel)


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

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": schema,
            },
        )
        text = response.text or ""
        return validate_structured_output(text, schema=schema, source="gemini")

    def generate_text(self, prompt: str) -> str:
        """Generate free text for final user-facing output."""

        response = self.client.models.generate_content(model=self.model, contents=prompt)
        return (response.text or "").strip()
