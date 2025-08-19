"""Simple logging configuration for jockey."""

import logging
import sys
from typing import Optional

from .environment import LOG_LEVEL


def setup_logger(name: str = "jockey", level: Optional[str] = None) -> logging.Logger:
    """Set up a simple logger with console output.

    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Don't add handlers if they already exist
    if logger.handlers:
        return logger

    # Set level
    if level:
        logger.setLevel(getattr(logging, level.upper()))
    else:
        logger.setLevel(getattr(logging, LOG_LEVEL))

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logger.level)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(handler)

    return logger


# Default logger instance
logger = setup_logger()
