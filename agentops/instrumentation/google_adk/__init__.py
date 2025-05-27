"""Google ADK Instrumentation for AgentOps

This module provides instrumentation for Google's Agent Development Kit (ADK),
capturing agent execution, LLM calls, tool calls, and other ADK-specific events.
"""

from agentops.instrumentation.google_adk.version import LIBRARY_NAME, LIBRARY_VERSION
from agentops.instrumentation.google_adk.instrumentor import GoogleADKInstrumentor
from agentops.instrumentation.google_adk import patch

__all__ = ["LIBRARY_NAME", "LIBRARY_VERSION", "GoogleADKInstrumentor", "patch"]
