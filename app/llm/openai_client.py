"""OpenAI client wrapper for planning and synthesis."""

from __future__ import annotations

from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel

from app.config import get_settings
from app.llm.json_response import validate_structured_output

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class OpenAIClient:
    """Thin wrapper around the OpenAI Responses API."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai.")
        self.model = settings.openai_model
        self.client = OpenAI(api_key=settings.openai_api_key)

    def generate_json(self, prompt: str, schema: type[SchemaT]) -> SchemaT:
        """Generate schema-constrained JSON and return a validated model."""

        response = self.client.responses.parse(model=self.model, input=prompt, text_format=schema)
        if response.output_parsed is not None:
            return validate_structured_output(response.output_parsed, schema=schema, source="openai")
        text = response.output_text or ""
        return validate_structured_output(text, schema=schema, source="openai")

    def generate_text(self, prompt: str) -> str:
        """Generate free text for final user-facing output."""

        response = self.client.responses.create(model=self.model, input=prompt)
        return (response.output_text or "").strip()
