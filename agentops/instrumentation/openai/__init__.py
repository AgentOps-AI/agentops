"""OpenAI API instrumentation for AgentOps.

This package provides OpenTelemetry-based instrumentation for OpenAI API calls,
extending the third-party instrumentation to add support for OpenAI responses.
"""

from agentops.logging import logger


def get_version() -> str:
    """Get the version of the agents SDK, or 'unknown' if not found"""
    try:
        from importlib.metadata import version

        return version("openai")
    except ImportError:
        logger.debug("Could not find OpenAI Agents SDK version")
        return "unknown"


LIBRARY_NAME = "openai"
LIBRARY_VERSION: str = get_version()

# Import after defining constants to avoid circular imports
from agentops.instrumentation.openai.instrumentor import OpenAIInstrumentor  # noqa: E402

__all__ = [
    "LIBRARY_NAME",
    "LIBRARY_VERSION",
    "OpenAIInstrumentor",
]
