"""OpenAI client wrapper for planning and synthesis."""

from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI

from app.config import get_settings


class OpenAIClient:
    """Thin wrapper around the OpenAI Responses API."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai.")
        self.model = settings.openai_model
        self.client = OpenAI(api_key=settings.openai_api_key)

    def generate_json(self, prompt: str) -> dict[str, Any]:
        """Generate JSON and parse the model response strictly."""

        response = self.client.responses.create(model=self.model, input=prompt)
        text = response.output_text or ""
        return self._parse_json(text)

    def generate_text(self, prompt: str) -> str:
        """Generate free text for final user-facing output."""

        response = self.client.responses.create(model=self.model, input=prompt)
        return (response.output_text or "").strip()

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        """Parse the first JSON object found in the model response."""

        stripped = text.strip()
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", stripped, re.DOTALL)
            if not match:
                raise ValueError(f"OpenAI response was not valid JSON: {text}")
            return json.loads(match.group(0))
