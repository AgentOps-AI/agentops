"""Google Generative AI (Gemini) API instrumentation.

This module provides instrumentation for the Google Generative AI (Gemini) API,
including content generation, streaming, and chat functionality.
"""

import logging


def get_version() -> str:
    """Get the version of the Google Generative AI SDK, or 'unknown' if not found

    Attempts to retrieve the installed version of the Google Generative AI SDK using importlib.metadata.
    Falls back to 'unknown' if the version cannot be determined.

    Returns:
        The version string of the Google Generative AI SDK or 'unknown'
    """
    try:
        from importlib.metadata import version

        return version("google-genai")
    except ImportError:
        logger.debug("Could not find Google Generative AI SDK version")
        return "unknown"


LIBRARY_NAME = "google-genai"
LIBRARY_VERSION: str = get_version()

logger = logging.getLogger(__name__)

# Import after defining constants to avoid circular imports
from agentops.instrumentation.google_generativeai.instrumentor import GoogleGenerativeAIInstrumentor  # noqa: E402

__all__ = [
    "LIBRARY_NAME",
    "LIBRARY_VERSION",
    "GoogleGenerativeAIInstrumentor",
]
