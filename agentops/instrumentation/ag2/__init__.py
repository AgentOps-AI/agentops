"""AG2 Instrumentation for AgentOps

This module provides instrumentation for AG2 (AutoGen), adding telemetry to track agent
interactions, conversation flows, and tool usage while focusing on summary-level data rather
than individual message exchanges.
"""

from agentops.instrumentation.ag2.instrumentor import AG2Instrumentor
from agentops.instrumentation.ag2.version import LIBRARY_NAME, LIBRARY_VERSION

__all__ = ["AG2Instrumentor", "LIBRARY_NAME", "LIBRARY_VERSION"]
