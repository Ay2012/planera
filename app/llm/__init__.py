"""LLM integrations."""

from __future__ import annotations

from app.config import get_settings


def get_llm_client():
    """Return the active LLM client based on settings."""

    provider = get_settings().llm_provider.lower().strip()
    if provider == "openai":
        from app.llm.openai_client import OpenAIClient

        return OpenAIClient()
    if provider == "gemini":
        from app.llm.gemini import GeminiClient

        return GeminiClient()
    raise ValueError(f"Unsupported LLM_PROVIDER '{get_settings().llm_provider}'. Use 'openai' or 'gemini'.")
