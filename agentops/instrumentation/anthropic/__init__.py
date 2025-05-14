"""Anthropic API instrumentation.

This module provides instrumentation for the Anthropic API,
including chat completions, streaming, and event handling.
"""

import logging


def get_version() -> str:
    """Get the version of the Anthropic SDK, or 'unknown' if not found

    Attempts to retrieve the installed version of the Anthropic SDK using importlib.metadata.
    Falls back to 'unknown' if the version cannot be determined.

    Returns:
        The version string of the Anthropic SDK or 'unknown'
    """
    try:
        from importlib.metadata import version

        return version("anthropic")
    except ImportError:
        logger.debug("Could not find Anthropic SDK version")
        return "unknown"


LIBRARY_NAME = "anthropic"
LIBRARY_VERSION: str = get_version()

logger = logging.getLogger(__name__)

# Import after defining constants to avoid circular imports
from agentops.instrumentation.anthropic.instrumentor import AnthropicInstrumentor  # noqa: E402

__all__ = [
    "LIBRARY_NAME",
    "LIBRARY_VERSION",
    "AnthropicInstrumentor",
]
