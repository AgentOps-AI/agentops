# MCP Agent Integration for AgentOps

This module provides integration between MCP Agent and AgentOps for comprehensive observability and monitoring of agent operations, tool calls, and workflow execution.

## Overview

MCP Agent is a framework for building effective agents with Model Context Protocol (MCP). This integration hooks into MCP Agent's existing telemetry system to capture:

- Agent operations and workflow execution
- Tool calls and their results
- Session and context information
- Error handling and debugging information

## Features

- **Automatic Instrumentation**: Hooks into MCP Agent's telemetry system automatically
- **Enhanced Spans**: Adds AgentOps-specific attributes to all MCP Agent spans
- **Tool Call Tracking**: Captures tool execution details and results
- **Session Management**: Tracks session IDs and context information
- **Error Handling**: Comprehensive error tracking and debugging support

## Installation

The integration is automatically available when both `agentops` and `mcp-agent` are installed:

```bash
pip install agentops mcp-agent
```

## Usage

### Automatic Integration

The integration works automatically when you import both libraries:

```python
import agentops
import mcp_agent

# Initialize AgentOps
agentops.init("your-api-key")

# Your MCP Agent code will be automatically instrumented
from mcp_agent.core.context import Context
from mcp_agent.tracing.telemetry import telemetry

@telemetry.traced("my_agent_operation")
def my_agent_function():
    # This will be automatically captured by AgentOps
    pass
```

### Manual Integration

You can also manually control the integration:

```python
from agentops.instrumentation.agentic.mcp_agent import (
    hook_mcp_agent_telemetry,
    unhook_mcp_agent_telemetry,
    mcp_agent_span,
    mcp_agent_traced
)

# Hook into MCP Agent telemetry
hook_mcp_agent_telemetry()

# Use custom spans
with mcp_agent_span(
    "custom_operation",
    operation="my_custom_operation",
    session_id="session-123",
    agent_name="my_agent"
):
    # Your code here
    pass

# Use custom decorators
@mcp_agent_traced(
    name="decorated_function",
    operation="my_decorated_operation",
    agent_name="my_agent"
)
def my_function():
    pass
```

### Enhanced Spans

You can enhance existing MCP Agent spans with additional AgentOps attributes:

```python
from agentops.instrumentation.agentic.mcp_agent import enhance_mcp_agent_span
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("my_span") as span:
    # Enhance the span with MCP Agent attributes
    enhance_mcp_agent_span(
        span,
        operation="my_operation",
        session_id="session-123",
        agent_name="my_agent",
        workflow_id="workflow-456"
    )
```

## Configuration

### Environment Variables

- `AGENTOPS_MCP_AGENT_METRICS_ENABLED`: Enable/disable metrics collection (default: true)

### AgentOps Configuration

The integration respects all standard AgentOps configuration options:

```python
import agentops

agentops.init(
    api_key="your-api-key",
    application_name="my-mcp-agent-app",
    environment="production"
)
```

## Captured Data

### Span Attributes

The integration captures the following MCP Agent specific attributes:

- `mcp_agent.operation`: The operation being performed
- `mcp_agent.session_id`: Session identifier
- `mcp_agent.context_id`: Context identifier
- `mcp_agent.workflow_id`: Workflow identifier
- `mcp_agent.agent_id`: Agent identifier
- `mcp_agent.agent_name`: Human-readable agent name
- `mcp_agent.agent_description`: Agent description
- `mcp_agent.function`: Function name being executed
- `mcp_agent.module`: Module name

### Tool Call Attributes

For tool executions, additional attributes are captured:

- `mcp_agent.tool_name`: Name of the tool being called
- `mcp_agent.tool_description`: Tool description
- `mcp_agent.tool_arguments`: Tool arguments
- `mcp_agent.tool_result_content`: Tool result content
- `mcp_agent.tool_result_type`: Type of tool result
- `mcp_agent.tool_error`: Whether the tool call resulted in an error
- `mcp_agent.tool_error_message`: Error message if applicable

## Examples

### Basic Agent Usage

```python
import agentops
from mcp_agent.core.context import Context
from mcp_agent.tracing.telemetry import telemetry

# Initialize AgentOps
agentops.init("your-api-key")

@telemetry.traced("agent_execution")
def run_agent(context: Context):
    # This will be automatically captured with full context
    result = context.run_agent("my_agent")
    return result
```

### Custom Tool Integration

```python
from agentops.instrumentation.agentic.mcp_agent import mcp_agent_span

def custom_tool_call(tool_name: str, arguments: dict):
    with mcp_agent_span(
        f"tool_call.{tool_name}",
        operation="tool_execution",
        tool_name=tool_name,
        tool_arguments=arguments
    ):
        # Tool execution logic
        result = execute_tool(tool_name, arguments)
        return result
```

### Workflow Tracking

```python
from agentops.instrumentation.agentic.mcp_agent import mcp_agent_traced

@mcp_agent_traced(
    name="workflow_execution",
    operation="workflow",
    workflow_id="workflow-123",
    agent_name="workflow_agent"
)
def execute_workflow(workflow_config: dict):
    # Workflow execution logic
    pass
```

## Troubleshooting

### Common Issues

1. **Integration not working**: Ensure both `agentops` and `mcp-agent` are installed and imported
2. **Missing spans**: Check that AgentOps is properly initialized with a valid API key
3. **Telemetry conflicts**: The integration is designed to work alongside MCP Agent's existing telemetry

### Debug Mode

Enable debug logging to see detailed integration information:

```python
import logging
logging.getLogger("agentops.instrumentation.agentic.mcp_agent").setLevel(logging.DEBUG)
```

## API Reference

### Functions

- `hook_mcp_agent_telemetry()`: Hook into MCP Agent's telemetry system
- `unhook_mcp_agent_telemetry()`: Unhook from MCP Agent's telemetry system
- `enhance_mcp_agent_span(span, **attributes)`: Enhance an existing span with MCP Agent attributes
- `mcp_agent_span(name, **kwargs)`: Context manager for creating MCP Agent spans
- `mcp_agent_traced(**kwargs)`: Decorator for MCP Agent functions

### Classes

- `MCPAgentInstrumentor`: Main instrumentor class
- `MCPAgentTelemetryHook`: Telemetry hook implementation
- `MCPAgentSpanAttributes`: Span attribute definitions

## Contributing

To contribute to this integration:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This integration is part of the AgentOps project and follows the same license terms.