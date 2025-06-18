"""Anthropic API instrumentation.

This module provides instrumentation for the Anthropic API,
including chat completions, streaming, and event handling.
"""

import logging
from agentops.instrumentation.common import LibraryInfo

logger = logging.getLogger(__name__)

# Library information
_library_info = LibraryInfo(name="anthropic")
LIBRARY_NAME = _library_info.name
LIBRARY_VERSION = _library_info.version

# Import after defining constants to avoid circular imports
from agentops.instrumentation.providers.anthropic.instrumentor import AnthropicInstrumentor  # noqa: E402

__all__ = [
    "LIBRARY_NAME",
    "LIBRARY_VERSION",
    "AnthropicInstrumentor",
]
