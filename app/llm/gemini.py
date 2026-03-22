"""Gemini client wrapper for planning and synthesis."""

from __future__ import annotations

import json
import re
from typing import Any

from google import genai

from app.config import get_settings


class GeminiClient:
    """Thin wrapper around the Gemini API."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required for the agentic workflow.")
        self.model = settings.gemini_model
        self.client = genai.Client(api_key=settings.gemini_api_key)

    def generate_json(self, prompt: str) -> dict[str, Any]:
        """Generate JSON and parse the model response strictly."""

        response = self.client.models.generate_content(model=self.model, contents=prompt)
        text = response.text or ""
        return self._parse_json(text)

    def generate_text(self, prompt: str) -> str:
        """Generate free text for final user-facing output."""

        response = self.client.models.generate_content(model=self.model, contents=prompt)
        return (response.text or "").strip()

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        """Parse the first JSON object found in the model response."""

        stripped = text.strip()
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", stripped, re.DOTALL)
            if not match:
                raise ValueError(f"Gemini response was not valid JSON: {text}")
            return json.loads(match.group(0))
