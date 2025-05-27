"""AG2 Instrumentation for AgentOps

This module provides instrumentation for AG2 (AutoGen), adding telemetry to track agent
interactions, conversation flows, and tool usage while focusing on summary-level data rather
than individual message exchanges.
"""

from agentops.logging import logger


def get_version() -> str:
    """Get the version of the AG2 package, or 'unknown' if not found"""
    try:
        from importlib.metadata import version

        return version("ag2")
    except ImportError:
        logger.debug("Could not find AG2 version")
        return "unknown"


LIBRARY_NAME = "ag2"
LIBRARY_VERSION: str = get_version()

# Import after defining constants to avoid circular imports
from agentops.instrumentation.ag2.instrumentor import AG2Instrumentor  # noqa: E402

__all__ = ["AG2Instrumentor", "LIBRARY_NAME", "LIBRARY_VERSION"]
