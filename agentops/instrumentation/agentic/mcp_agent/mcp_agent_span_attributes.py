"""
MCP Agent specific span attributes for AgentOps instrumentation.
"""

from typing import Any, Dict, Optional
from opentelemetry.trace import Span

from agentops.semconv import SpanAttributes, AgentOpsSpanKindValues, ToolAttributes, MessageAttributes
from agentops.semconv.core import CoreAttributes


class MCPAgentSpanAttributes:
    """MCP Agent specific span attributes."""

    # MCP Agent specific attributes
    MCP_AGENT_OPERATION = "mcp_agent.operation"
    MCP_AGENT_TOOL_CALL = "mcp_agent.tool_call"
    MCP_AGENT_TOOL_RESULT = "mcp_agent.tool_result"
    MCP_AGENT_SESSION_ID = "mcp_agent.session_id"
    MCP_AGENT_CONTEXT_ID = "mcp_agent.context_id"
    MCP_AGENT_WORKFLOW_ID = "mcp_agent.workflow_id"
    MCP_AGENT_AGENT_ID = "mcp_agent.agent_id"
    MCP_AGENT_AGENT_NAME = "mcp_agent.agent_name"
    MCP_AGENT_AGENT_DESCRIPTION = "mcp_agent.agent_description"
    MCP_AGENT_TOOL_NAME = "mcp_agent.tool_name"
    MCP_AGENT_TOOL_DESCRIPTION = "mcp_agent.tool_description"
    MCP_AGENT_TOOL_ARGUMENTS = "mcp_agent.tool_arguments"
    MCP_AGENT_TOOL_RESULT_CONTENT = "mcp_agent.tool_result_content"
    MCP_AGENT_TOOL_RESULT_TYPE = "mcp_agent.tool_result_type"
    MCP_AGENT_TOOL_ERROR = "mcp_agent.tool_error"
    MCP_AGENT_TOOL_ERROR_MESSAGE = "mcp_agent.tool_error_message"


def set_span_attribute(span: Span, key: str, value: Any) -> None:
    """Set a span attribute if the value is not None."""
    if value is not None:
        span.set_attribute(key, str(value))


def set_mcp_agent_span_attributes(
    span: Span,
    operation: Optional[str] = None,
    session_id: Optional[str] = None,
    context_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    agent_description: Optional[str] = None,
    **kwargs
) -> None:
    """Set MCP Agent specific span attributes."""
    set_span_attribute(span, MCPAgentSpanAttributes.MCP_AGENT_OPERATION, operation)
    set_span_attribute(span, MCPAgentSpanAttributes.MCP_AGENT_SESSION_ID, session_id)
    set_span_attribute(span, MCPAgentSpanAttributes.MCP_AGENT_CONTEXT_ID, context_id)
    set_span_attribute(span, MCPAgentSpanAttributes.MCP_AGENT_WORKFLOW_ID, workflow_id)
    set_span_attribute(span, MCPAgentSpanAttributes.MCP_AGENT_AGENT_ID, agent_id)
    set_span_attribute(span, MCPAgentSpanAttributes.MCP_AGENT_AGENT_NAME, agent_name)
    set_span_attribute(span, MCPAgentSpanAttributes.MCP_AGENT_AGENT_DESCRIPTION, agent_description)
    
    # Set any additional attributes
    for key, value in kwargs.items():
        if value is not None:
            span.set_attribute(f"mcp_agent.{key}", str(value))


def set_mcp_agent_tool_attributes(
    span: Span,
    tool_name: Optional[str] = None,
    tool_description: Optional[str] = None,
    tool_arguments: Optional[Dict[str, Any]] = None,
    tool_result_content: Optional[str] = None,
    tool_result_type: Optional[str] = None,
    tool_error: Optional[bool] = None,
    tool_error_message: Optional[str] = None,
) -> None:
    """Set MCP Agent tool specific span attributes."""
    set_span_attribute(span, MCPAgentSpanAttributes.MCP_AGENT_TOOL_NAME, tool_name)
    set_span_attribute(span, MCPAgentSpanAttributes.MCP_AGENT_TOOL_DESCRIPTION, tool_description)
    set_span_attribute(span, MCPAgentSpanAttributes.MCP_AGENT_TOOL_ARGUMENTS, str(tool_arguments) if tool_arguments else None)
    set_span_attribute(span, MCPAgentSpanAttributes.MCP_AGENT_TOOL_RESULT_CONTENT, tool_result_content)
    set_span_attribute(span, MCPAgentSpanAttributes.MCP_AGENT_TOOL_RESULT_TYPE, tool_result_type)
    set_span_attribute(span, MCPAgentSpanAttributes.MCP_AGENT_TOOL_ERROR, tool_error)
    set_span_attribute(span, MCPAgentSpanAttributes.MCP_AGENT_TOOL_ERROR_MESSAGE, tool_error_message)