"""Google ADK Instrumentation for AgentOps

This module provides instrumentation for Google's Agent Development Kit (ADK),
capturing agent execution, LLM calls, tool calls, and other ADK-specific events.
"""

from agentops.instrumentation.common import LibraryInfo

# Library information
_library_info = LibraryInfo(
    name="agentops.instrumentation.google_adk", package_name="google-adk", default_version="0.0.0"
)
LIBRARY_NAME = _library_info.name
LIBRARY_VERSION = _library_info.version

from agentops.instrumentation.agentic.google_adk.instrumentor import GooogleAdkInstrumentor  # noqa: E402
from agentops.instrumentation.agentic.google_adk import patch  # noqa: E402

__all__ = ["LIBRARY_NAME", "LIBRARY_VERSION", "GooogleAdkInstrumentor", "patch"]
