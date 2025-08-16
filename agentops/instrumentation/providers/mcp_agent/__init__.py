"""MCP Agent instrumentation for AgentOps.

This package provides OpenTelemetry-based instrumentation for MCP Agent,
enabling telemetry collection and tracing for MCP-based agent workflows.
"""

from agentops.instrumentation.common import LibraryInfo

# Library information
_library_info = LibraryInfo(name="mcp-agent")
LIBRARY_NAME = _library_info.name
LIBRARY_VERSION = _library_info.version

# Import after defining constants to avoid circular imports
from agentops.instrumentation.providers.mcp_agent.instrumentor import MCPAgentInstrumentor  # noqa: E402

__all__ = [
    "LIBRARY_NAME",
    "LIBRARY_VERSION",
    "MCPAgentInstrumentor",
]