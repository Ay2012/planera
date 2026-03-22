"""Extract JSON objects from LLM text; tolerate unescaped newlines in strings (e.g. SQL)."""

from __future__ import annotations

import json
import re
from typing import Any

from app.utils.logging import get_logger

logger = get_logger(__name__)

_MAX_SNIPPET = 8000


def _truncate(s: str, max_len: int = _MAX_SNIPPET) -> str:
    if len(s) <= max_len:
        return s
    half = max_len // 2
    return s[:half] + "\n...[truncated]...\n" + s[-half:]


def parse_llm_json_object(text: str, *, source: str = "llm") -> dict[str, Any]:
    """Parse the first JSON object from model output.

    Uses :func:`json.loads` with ``strict=False`` so literal control characters inside
    string values are accepted. Models often emit multi-line SQL without ``\\n`` escapes,
    which strict JSON rejects with "Invalid control character".
    """

    stripped = (text or "").strip()
    if not stripped:
        logger.warning("[%s] Empty body for JSON parse", source)
        raise ValueError(f"{source}: empty response for JSON parsing")

    def as_dict(parsed: Any) -> dict[str, Any]:
        if not isinstance(parsed, dict):
            logger.warning("[%s] Top-level JSON is %s, not an object", source, type(parsed).__name__)
            raise ValueError(f"{source}: expected JSON object, got {type(parsed).__name__}")
        return parsed

    try:
        parsed = json.loads(stripped, strict=False)
        out = as_dict(parsed)
        logger.debug("[%s] Parsed JSON (%d chars) keys=%s", source, len(stripped), list(out.keys()))
        return out
    except json.JSONDecodeError as e:
        logger.warning(
            "[%s] JSON parse failed (primary): %s at line %s col %s (pos %s)",
            source,
            e.msg,
            e.lineno,
            e.colno,
            e.pos,
        )

    match = re.search(r"\{.*\}", stripped, re.DOTALL)
    if not match:
        logger.warning("[%s] No JSON object found; excerpt=%s", source, repr(_truncate(stripped)))
        raise ValueError(f"{source}: response was not a JSON object: {_truncate(stripped, 500)}")

    fragment = match.group(0)
    try:
        parsed = json.loads(fragment, strict=False)
        out = as_dict(parsed)
        logger.info("[%s] Parsed JSON after extracting object fragment (%d chars)", source, len(fragment))
        return out
    except json.JSONDecodeError as e2:
        logger.warning(
            "[%s] JSON parse failed (fragment): %s at line %s col %s; excerpt=%s",
            source,
            e2.msg,
            e2.lineno,
            e2.colno,
            repr(_truncate(fragment, 1200)),
        )
        raise ValueError(f"{source}: could not parse JSON from model output: {e2.msg}") from e2
