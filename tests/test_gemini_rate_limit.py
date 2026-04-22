"""Sliding-window rate limit for Gemini API (free-tier RPM)."""

from __future__ import annotations

import time

import pytest

from app.config import get_settings
from app.llm import gemini as gemini_mod


@pytest.fixture
def clear_gemini_rate_deque() -> None:
    gemini_mod._request_times.clear()
    yield
    gemini_mod._request_times.clear()
    get_settings.cache_clear()


def test_acquire_allows_bursts_up_to_max_then_waits(
    monkeypatch: pytest.MonkeyPatch,
    clear_gemini_rate_deque: None,
) -> None:
    """With max=2 in a 150ms window, the third slot must wait until the window slides."""
    monkeypatch.setenv("GEMINI_MAX_REQUESTS_PER_MINUTE", "2")
    monkeypatch.setenv("GEMINI_RATE_LIMIT_WINDOW_SECONDS", "0.15")
    get_settings.cache_clear()
    t0 = time.perf_counter()
    gemini_mod._acquire_gemini_request_slot()
    gemini_mod._acquire_gemini_request_slot()
    gemini_mod._acquire_gemini_request_slot()
    elapsed = time.perf_counter() - t0
    get_settings.cache_clear()
    assert elapsed >= 0.12, "third acquire should block until a slot is released"


def test_acquire_is_noop_when_max_zero(
    monkeypatch: pytest.MonkeyPatch,
    clear_gemini_rate_deque: None,
) -> None:
    monkeypatch.setenv("GEMINI_MAX_REQUESTS_PER_MINUTE", "0")
    get_settings.cache_clear()
    t0 = time.perf_counter()
    for _ in range(5):
        gemini_mod._acquire_gemini_request_slot()
    assert time.perf_counter() - t0 < 0.1
    get_settings.cache_clear()
