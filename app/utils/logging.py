"""Logging configuration helpers."""

from __future__ import annotations

import logging


def configure_logging(level: str = "INFO") -> None:
    """Configure process-wide logging once."""

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def get_logger(name: str) -> logging.Logger:
    """Return a standard logger instance."""

    return logging.getLogger(name)
