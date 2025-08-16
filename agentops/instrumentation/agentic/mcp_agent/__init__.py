from agentops.instrumentation.common import LibraryInfo

# Library information for MCP Agent integration
# Note: The pip package name is "mcp-agent" while the import path is "mcp_agent".
_library_info = LibraryInfo(name="mcp_agent", package_name="mcp-agent")
LIBRARY_NAME = _library_info.name
LIBRARY_VERSION = _library_info.version

# Import after defining constants to avoid circular imports
from agentops.instrumentation.agentic.mcp_agent.instrumentor import MCPAgentInstrumentor  # noqa: E402

__all__ = [
    "MCPAgentInstrumentor",
    "LIBRARY_NAME",
    "LIBRARY_VERSION",
]