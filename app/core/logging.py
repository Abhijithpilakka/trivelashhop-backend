"""
app/core/logging.py
-------------------
Structured JSON logging via structlog.
In development: pretty coloured console output.
In production: JSON lines (works with Railway / Render log drains).
"""

from __future__ import annotations

import logging
import sys

import structlog
from structlog.types import EventDict, Processor

from app.core.config import get_settings


def _drop_color_message_key(_, __, event_dict: EventDict) -> EventDict:
    """Remove the `color_message` key added by uvicorn."""
    event_dict.pop("color_message", None)
    return event_dict


def _safe_add_logger_name(logger, method_name, event_dict: EventDict) -> EventDict:
    event_dict["logger"] = getattr(logger, "name", "") or ""
    return event_dict


def setup_logging() -> None:
    settings = get_settings()

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        _safe_add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        _drop_color_message_key,
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.is_production:
        # JSON for log aggregators
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
        renderer = logging.StreamHandler(sys.stdout)
    else:
        # Pretty for local development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
        renderer = logging.StreamHandler(sys.stdout)

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(renderer.stream),
        cache_logger_on_first_use=True,
    )

    # Also configure stdlib logging so uvicorn / SQLAlchemy logs go through structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
    )


def get_logger(name: str | None = None):
    return structlog.get_logger(name)
