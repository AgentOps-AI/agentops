# MCP Agent Integration Guide

This guide explains how to integrate MCP Agent with AgentOps for comprehensive observability and monitoring.

## Quick Start

### 1. Install Dependencies

```bash
pip install agentops mcp-agent
```

### 2. Initialize AgentOps

```python
import agentops

# Initialize AgentOps with your API key
agentops.init("your-api-key-here")
```

### 3. Use MCP Agent

The integration works automatically when both libraries are imported:

```python
import mcp_agent
from mcp_agent.tracing.telemetry import telemetry

@telemetry.traced("my_agent_operation")
def my_agent_function():
    # This will be automatically captured by AgentOps
    return "result"
```

## Integration Methods

### Method 1: Automatic Integration (Recommended)

The integration automatically hooks into MCP Agent's telemetry system when both libraries are imported:

```python
import agentops
import mcp_agent

# Initialize AgentOps
agentops.init("your-api-key")

# Use MCP Agent normally - everything is automatically captured
from mcp_agent.core.context import Context
from mcp_agent.tracing.telemetry import telemetry

@telemetry.traced("agent_execution")
def run_agent(context: Context):
    result = context.run_agent("my_agent")
    return result
```

### Method 2: Manual Integration

For more control, you can manually hook into the telemetry system:

```python
from agentops.instrumentation.agentic.mcp_agent import (
    hook_mcp_agent_telemetry,
    unhook_mcp_agent_telemetry
)

# Hook into MCP Agent telemetry
hook_mcp_agent_telemetry()

# Your MCP Agent code here...

# Unhook when done (optional)
unhook_mcp_agent_telemetry()
```

### Method 3: Custom Spans

Create custom spans with MCP Agent context:

```python
from agentops.instrumentation.agentic.mcp_agent import mcp_agent_span

def custom_workflow():
    with mcp_agent_span(
        "custom_workflow",
        operation="workflow_execution",
        session_id="session-123",
        agent_name="my_agent",
        workflow_id="workflow-456"
    ):
        # Your workflow logic here
        result = execute_workflow()
        return result
```

### Method 4: Custom Decorators

Use custom decorators for functions:

```python
from agentops.instrumentation.agentic.mcp_agent import mcp_agent_traced

@mcp_agent_traced(
    name="decorated_function",
    operation="my_operation",
    agent_name="my_agent",
    session_id="session-789"
)
def my_function():
    # This function will be captured with the specified attributes
    return "result"
```

## Advanced Usage

### Enhancing Existing Spans

You can enhance existing OpenTelemetry spans with MCP Agent context:

```python
from opentelemetry import trace
from agentops.instrumentation.agentic.mcp_agent import enhance_mcp_agent_span

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("external_span") as span:
    # Enhance the span with MCP Agent attributes
    enhance_mcp_agent_span(
        span,
        operation="external_operation",
        session_id="session-123",
        agent_name="external_agent"
    )
    
    # Your code here
```

### Tool Call Tracking

Track tool calls with detailed information:

```python
from agentops.instrumentation.agentic.mcp_agent import mcp_agent_span

def execute_tool(tool_name: str, arguments: dict):
    with mcp_agent_span(
        f"tool_call.{tool_name}",
        operation="tool_execution",
        tool_name=tool_name,
        tool_arguments=arguments
    ):
        try:
            result = call_tool(tool_name, arguments)
            return result
        except Exception as e:
            # Error will be automatically captured
            raise
```

### Session Management

Track sessions and workflows:

```python
from agentops.instrumentation.agentic.mcp_agent import mcp_agent_span

def run_session(session_id: str, workflow_config: dict):
    with mcp_agent_span(
        "session_execution",
        operation="session",
        session_id=session_id,
        workflow_id=workflow_config.get("workflow_id")
    ):
        # Session execution logic
        for step in workflow_config["steps"]:
            execute_step(step)
```

## Configuration

### Environment Variables

- `AGENTOPS_MCP_AGENT_METRICS_ENABLED`: Enable/disable metrics collection (default: true)

### AgentOps Configuration

```python
import agentops

agentops.init(
    api_key="your-api-key",
    application_name="my-mcp-agent-app",
    environment="production",
    # Other configuration options...
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

For tool executions:

- `mcp_agent.tool_name`: Name of the tool being called
- `mcp_agent.tool_description`: Tool description
- `mcp_agent.tool_arguments`: Tool arguments
- `mcp_agent.tool_result_content`: Tool result content
- `mcp_agent.tool_result_type`: Type of tool result
- `mcp_agent.tool_error`: Whether the tool call resulted in an error
- `mcp_agent.tool_error_message`: Error message if applicable

## Best Practices

### 1. Use Descriptive Operation Names

```python
@telemetry.traced("agent.workflow.execution")  # Good
def execute_workflow():
    pass

@telemetry.traced("func")  # Avoid
def execute_workflow():
    pass
```

### 2. Include Context Information

```python
with mcp_agent_span(
    "workflow_execution",
    operation="workflow",
    session_id=session_id,
    agent_name=agent_name,
    workflow_id=workflow_id
):
    # Your code here
```

### 3. Handle Errors Gracefully

```python
@telemetry.traced("agent_operation")
def agent_operation():
    try:
        result = risky_operation()
        return result
    except Exception as e:
        # Error will be automatically captured by the integration
        logger.error(f"Operation failed: {e}")
        raise
```

### 4. Use Consistent Naming

```python
# Use consistent naming patterns
@telemetry.traced("agent.workflow.step1")
def step1():
    pass

@telemetry.traced("agent.workflow.step2")
def step2():
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

### Testing the Integration

Run the example to test the integration:

```python
from agentops.instrumentation.agentic.mcp_agent.example import example_mcp_agent_integration

example_mcp_agent_integration()
```

## Migration from Other Systems

### From Manual Instrumentation

If you were manually creating spans, you can now use the automatic integration:

```python
# Before (manual)
with tracer.start_as_current_span("agent_operation") as span:
    span.set_attribute("agent.name", "my_agent")
    # Your code here

# After (automatic)
@telemetry.traced("agent_operation")
def agent_operation():
    # Your code here - automatically captured
    pass
```

### From Other Observability Systems

The integration is designed to work alongside other observability systems. You can gradually migrate:

```python
# Keep existing instrumentation
with existing_tracer.start_span("legacy_span"):
    # Add MCP Agent integration
    with mcp_agent_span("mcp_agent_operation"):
        # Your code here
        pass
```

## Support

For issues and questions:

1. Check the troubleshooting section above
2. Review the example code
3. Enable debug logging for detailed information
4. Check the AgentOps documentation for general issues