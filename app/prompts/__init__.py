"""Jinja-backed prompt rendering helpers."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined


@lru_cache(maxsize=1)
def _prompt_environment() -> Environment:
    """Create a strict Jinja environment for workflow prompts."""

    templates_dir = Path(__file__).resolve().parent
    return Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=False,
        trim_blocks=False,
        lstrip_blocks=False,
        undefined=StrictUndefined,
    )


def render_prompt(template_name: str, **context: object) -> str:
    """Render one prompt template with the provided context."""

    template = _prompt_environment().get_template(template_name)
    return template.render(**context).strip()
