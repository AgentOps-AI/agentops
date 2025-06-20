"""AG2 Instrumentation for AgentOps

This module provides instrumentation for AG2 (AutoGen), adding telemetry to track agent
interactions, conversation flows, and tool usage while focusing on summary-level data rather
than individual message exchanges.
"""

from agentops.instrumentation.common import LibraryInfo

# Library information
_library_info = LibraryInfo(name="ag2")
LIBRARY_NAME = _library_info.name
LIBRARY_VERSION = _library_info.version

# Import after defining constants to avoid circular imports
from agentops.instrumentation.agentic.ag2.instrumentor import AG2Instrumentor  # noqa: E402

__all__ = ["AG2Instrumentor", "LIBRARY_NAME", "LIBRARY_VERSION"]
