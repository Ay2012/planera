"""Shared helpers for import-safe runtime stubs during staged implementation."""

from __future__ import annotations

from typing import NoReturn


def raise_not_implemented(feature: str) -> NoReturn:
    """Raise a consistent error while later workflow branches are still pending."""

    raise NotImplementedError(f"{feature} is not implemented on this branch yet.")
