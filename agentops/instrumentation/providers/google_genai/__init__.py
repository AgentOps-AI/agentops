"""Google Generative AI (Gemini) API instrumentation.

This module provides instrumentation for the Google Generative AI (Gemini) API,
including content generation, streaming, and chat functionality.
"""

from agentops.instrumentation.common.constants import setup_instrumentation_module

# Setup standard instrumentation components
LIBRARY_NAME, LIBRARY_VERSION, PACKAGE_VERSION, logger = setup_instrumentation_module(
    library_name="google-genai",
    library_version="1.0.0",
    package_name="google-genai",
    display_name="Google Generative AI SDK",
)

# Import after defining constants to avoid circular imports
from agentops.instrumentation.providers.google_genai.instrumentor import GoogleGenAIInstrumentor  # noqa: E402

__all__ = [
    "LIBRARY_NAME",
    "LIBRARY_VERSION",
    "PACKAGE_VERSION",
    "GoogleGenAIInstrumentor",
]
