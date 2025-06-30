"""Logging configuration for Vosk Voice Assistant."""

import logging
import sys

from .config import settings


def setup_logging(
    level: str | None = None,
    format_string: str | None = None,
) -> None:
    """Setup application logging.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom log format string
    """
    log_level = level or settings.log_level
    log_format = format_string or settings.log_format

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Set specific logger levels
    logging.getLogger("vosk").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name.

    Args:
        name: Logger name

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
