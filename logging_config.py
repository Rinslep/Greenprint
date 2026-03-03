"""Structured logging configuration using structlog.

Two modes controlled by Settings.log_mode:
  - "dev":  Pretty-printed colourised console output, DEBUG level
  - "prod": JSON output (one object per line), INFO level (configurable via LOG_LEVEL)
"""

import logging
import structlog

from config import settings


def configure_logging(dev_mode: bool | None = None) -> None:
    if dev_mode is None:
        dev_mode = settings.log_mode == "dev"

    level = logging.DEBUG if dev_mode else getattr(logging, settings.log_level.upper(), logging.INFO)

    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if dev_mode:
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(format="%(message)s", level=level, force=True)
