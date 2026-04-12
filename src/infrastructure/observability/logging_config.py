"""Structured JSON logging configuration using structlog.

Configures structlog with:
- JSON renderer for production (machine-parseable)
- ConsoleRenderer for local development (human-readable)
- Automatic timestamping (ISO-8601 UTC)
- Log level filtering bound to Python's stdlib logging
"""

from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(level: str = "INFO") -> None:
    """Configure structlog and stdlib logging for the entire process.

    Should be called once at application startup (composition root).
    Subsequent calls are idempotent — structlog re-configuration is safe.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               Case-insensitive.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Stdlib root logger — catches logs from third-party libraries
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.ExceptionRenderer(),
    ]

    is_tty = sys.stdout.isatty()

    if is_tty:
        # Human-readable for local development
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer()
    else:
        # Machine-parseable JSON for containers / production
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)
