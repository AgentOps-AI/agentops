"""OpenAI API instrumentation for AgentOps.

This package provides OpenTelemetry-based instrumentation for OpenAI API calls,
extending the third-party instrumentation to add support for OpenAI responses.
"""

from agentops.instrumentation.common import LibraryInfo

# Library information
_library_info = LibraryInfo(name="openai")
LIBRARY_NAME = _library_info.name
LIBRARY_VERSION = _library_info.version

# Import after defining constants to avoid circular imports
from agentops.instrumentation.providers.openai.instrumentor import OpenaiInstrumentor  # noqa: E402

__all__ = [
    "LIBRARY_NAME",
    "LIBRARY_VERSION",
    "OpenaiInstrumentor",
]
