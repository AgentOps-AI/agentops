"""Google Generative AI (Gemini) API instrumentation.

This module provides instrumentation for the Google Generative AI (Gemini) API,
including content generation, streaming, and chat functionality.
"""

import logging
from agentops.instrumentation.common import LibraryInfo

logger = logging.getLogger(__name__)

# Library information
_library_info = LibraryInfo(name="google-genai")
LIBRARY_NAME = _library_info.name
LIBRARY_VERSION = _library_info.version

# Import after defining constants to avoid circular imports
from agentops.instrumentation.providers.google_genai.instrumentor import GoogleGenaiInstrumentor  # noqa: E402

__all__ = [
    "LIBRARY_NAME",
    "LIBRARY_VERSION",
    "GoogleGenaiInstrumentor",
]
