"""Gemini client wrapper for planning and synthesis."""

from __future__ import annotations

from typing import Any

from google import genai

from app.config import get_settings
from app.llm.json_response import parse_llm_json_object


class GeminiClient:
    """Thin wrapper around the Gemini API."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required for the agentic workflow.")
        self.model = settings.gemini_model
        self.client = genai.Client(api_key=settings.gemini_api_key)

    def generate_json(self, prompt: str) -> dict[str, Any]:
        """Generate JSON and parse the model response."""

        response = self.client.models.generate_content(model=self.model, contents=prompt)
        text = response.text or ""
        return parse_llm_json_object(text, source="gemini")

    def generate_text(self, prompt: str) -> str:
        """Generate free text for final user-facing output."""

        response = self.client.models.generate_content(model=self.model, contents=prompt)
        return (response.text or "").strip()
