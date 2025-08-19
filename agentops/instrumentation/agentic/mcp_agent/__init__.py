"""
AgentOps instrumentation for MCP Agent.

This module provides integration with MCP Agent's telemetry system to capture
agent operations, tool calls, and workflow execution for observability.
"""

from .instrumentation import (
    MCPAgentInstrumentor,
    instrument_mcp_agent,
    uninstrument_mcp_agent,
    instrument_mcp_agent_tool_calls,
)
from .mcp_agent_span_attributes import (
    MCPAgentSpanAttributes,
    set_mcp_agent_span_attributes,
    set_mcp_agent_tool_attributes,
)
from .telemetry_hook import (
    hook_mcp_agent_telemetry,
    unhook_mcp_agent_telemetry,
    enhance_mcp_agent_span,
    mcp_agent_span,
    mcp_agent_traced,
)
from .version import __version__

__all__ = [
    "MCPAgentInstrumentor",
    "instrument_mcp_agent",
    "uninstrument_mcp_agent",
    "instrument_mcp_agent_tool_calls",
    "MCPAgentSpanAttributes",
    "set_mcp_agent_span_attributes",
    "set_mcp_agent_tool_attributes",
    "hook_mcp_agent_telemetry",
    "unhook_mcp_agent_telemetry",
    "enhance_mcp_agent_span",
    "mcp_agent_span",
    "mcp_agent_traced",
    "__version__",
]