"""Shared compatibility helpers for temporarily unimplemented agent modules."""

from __future__ import annotations

from typing import NoReturn


def raise_not_implemented(feature: str) -> NoReturn:
    """Raise a consistent error for deferred runtime features."""

    raise NotImplementedError(
        f"{feature} is not implemented in the planner-input phase. "
        "This branch currently supports only raw-schema planner input construction."
    )
