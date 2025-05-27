"""Google ADK Instrumentation for AgentOps

This module provides instrumentation for Google's Agent Development Kit (ADK),
capturing agent execution, LLM calls, tool calls, and other ADK-specific events.
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("google-adk")
except PackageNotFoundError:
    __version__ = "0.0.0"

LIBRARY_NAME = "agentops.instrumentation.google_adk"
LIBRARY_VERSION = __version__

from agentops.instrumentation.google_adk.instrumentor import GoogleADKInstrumentor  # noqa: E402
from agentops.instrumentation.google_adk import patch  # noqa: E402

__all__ = ["LIBRARY_NAME", "LIBRARY_VERSION", "GoogleADKInstrumentor", "patch"]
