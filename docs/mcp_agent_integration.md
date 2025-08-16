# MCP Agent Integration with AgentOps

## Overview

AgentOps now provides comprehensive integration support for [MCP Agent](https://github.com/lastmile-ai/mcp-agent), enabling seamless telemetry collection and observability for MCP-based agent workflows. This integration hooks directly into MCP Agent's existing OpenTelemetry infrastructure while adding AgentOps-specific tracking and metrics.

## Features

### Telemetry Integration
- **Automatic instrumentation** of MCP Agent's TelemetryManager
- **Tracer configuration monitoring** to track when MCP Agent configures its tracing
- **Seamless integration** with existing OpenTelemetry setup
- **Optional override** of tracer configuration for custom exporters

### Comprehensive Tracking
- **Tool Calls**: Track all MCP tool invocations with arguments and results
- **Workflows**: Monitor workflow execution with input/output capture
- **Agent Execution**: Trace agent operations with prompt and completion tracking
- **Error Handling**: Automatic error capture and reporting

### Performance Metrics
- Tool call counters and duration
- Workflow execution duration
- Agent execution statistics
- Request/response metrics

## Installation

```bash
# Install AgentOps with MCP Agent support
pip install agentops

# Install MCP Agent (if not already installed)
pip install mcp-agent
```

## Quick Start

### Basic Usage

```python
import agentops
from mcp_agent import MCPAgent

# Initialize AgentOps (this automatically instruments MCP Agent)
agentops.init(api_key="your-api-key")

# Use MCP Agent as normal - telemetry is automatically captured
agent = MCPAgent()
result = await agent.execute("Your prompt here")

# End the session
agentops.end_session()
```

### Manual Instrumentation

If you need more control over the instrumentation:

```python
from agentops.instrumentation.providers.mcp_agent import MCPAgentInstrumentor
from agentops.instrumentation.providers.mcp_agent.config import Config

# Configure the instrumentor
config = Config(
    capture_prompts=True,
    capture_completions=True,
    capture_tool_calls=True,
    capture_workflows=True,
    max_prompt_length=10000,
    max_completion_length=10000,
)

# Create and apply instrumentation
instrumentor = MCPAgentInstrumentor(config)
instrumentor.instrument()

# Your MCP Agent code here...

# Clean up when done
instrumentor.uninstrument()
```

## Configuration Options

The MCP Agent integration can be configured with the following options:

### Data Capture Settings

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `capture_prompts` | bool | True | Capture prompts sent to agents |
| `capture_completions` | bool | True | Capture agent completions/responses |
| `capture_errors` | bool | True | Capture and report errors |
| `capture_tool_calls` | bool | True | Capture MCP tool calls and results |
| `capture_workflows` | bool | True | Capture workflow execution details |

### Integration Settings

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `integrate_with_existing_telemetry` | bool | True | Integrate with MCP Agent's existing OpenTelemetry setup |
| `override_tracer_config` | bool | False | Override MCP Agent's tracer configuration |

### Performance Settings

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `max_prompt_length` | int | 10000 | Maximum length of prompts to capture |
| `max_completion_length` | int | 10000 | Maximum length of completions to capture |

### Filtering Settings

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `excluded_tools` | list[str] | None | Tool names to exclude from instrumentation |
| `excluded_workflows` | list[str] | None | Workflow names to exclude from instrumentation |

## Advanced Usage

### Filtering Specific Tools or Workflows

```python
config = Config(
    excluded_tools=["debug_tool", "internal_tool"],
    excluded_workflows=["TestWorkflow"],
)
instrumentor = MCPAgentInstrumentor(config)
```

### Custom Telemetry Integration

The integration preserves MCP Agent's existing telemetry while adding AgentOps tracking:

```python
from mcp_agent.tracing.telemetry import telemetry

# MCP Agent's decorator still works as expected
@telemetry.traced("custom_operation")
async def my_function():
    # This will be tracked by both MCP Agent and AgentOps
    return await some_operation()
```

### Working with MCP Agent's TracingConfig

```python
from mcp_agent.config import OpenTelemetrySettings

# Configure MCP Agent's tracing
settings = OpenTelemetrySettings(
    enabled=True,
    exporters=["console", "otlp"],
    service_name="my-mcp-service",
)

# AgentOps will detect and integrate with this configuration
await tracing_config.configure(settings)
```

## Metrics and Observability

### Available Metrics

The integration provides the following metrics:

- `gen_ai.mcp_agent.tool_calls`: Number of MCP tool calls
- `gen_ai.mcp_agent.workflow_duration`: Duration of MCP Agent workflows
- `gen_ai.mcp_agent.executions`: Number of agent executions

### Span Attributes

Each span includes relevant attributes:

- `agent.type`: Always "mcp_agent"
- `agent.name`: Name of the specific agent
- `operation.type`: Type of operation (tool_call, workflow, agent_execution)
- `tool.name`: Name of the tool being called
- `workflow_name`: Name of the workflow
- `gen_ai.prompt`: Input prompt (if capture_prompts is enabled)
- `gen_ai.completion`: Output completion (if capture_completions is enabled)

## Troubleshooting

### Common Issues

1. **Instrumentation not working**: Ensure MCP Agent is imported before calling `agentops.init()`

2. **Missing telemetry data**: Check that the configuration options are set correctly

3. **Performance impact**: If experiencing performance issues, consider:
   - Reducing `max_prompt_length` and `max_completion_length`
   - Excluding non-critical tools/workflows
   - Disabling prompt/completion capture for high-volume operations

### Debug Logging

Enable debug logging to troubleshoot issues:

```python
import logging
logging.getLogger("agentops").setLevel(logging.DEBUG)
```

## Example: Complete Integration

```python
import asyncio
import agentops
from mcp_agent import MCPAgent
from mcp_agent.tools import Tool

# Initialize AgentOps
agentops.init(api_key="your-api-key")

# Define a custom tool
async def search_tool(query: str) -> str:
    # Tool implementation
    return f"Results for: {query}"

# Create MCP Agent with tools
agent = MCPAgent(
    tools=[
        Tool(
            name="search",
            description="Search for information",
            function=search_tool
        )
    ]
)

# Execute agent with automatic telemetry
async def main():
    result = await agent.execute(
        "Search for information about OpenTelemetry"
    )
    print(result)
    
    # End session with success
    agentops.end_session("Success")

# Run the example
asyncio.run(main())
```

## API Reference

### MCPAgentInstrumentor

```python
class MCPAgentInstrumentor:
    def __init__(self, config: Optional[Config] = None)
    def instrument(self, **kwargs) -> None
    def uninstrument(self, **kwargs) -> None
```

### Config

```python
@dataclass
class Config:
    capture_prompts: bool = True
    capture_completions: bool = True
    capture_errors: bool = True
    capture_tool_calls: bool = True
    capture_workflows: bool = True
    integrate_with_existing_telemetry: bool = True
    override_tracer_config: bool = False
    max_prompt_length: Optional[int] = 10000
    max_completion_length: Optional[int] = 10000
    excluded_tools: Optional[list[str]] = None
    excluded_workflows: Optional[list[str]] = None
```

## Contributing

We welcome contributions to improve the MCP Agent integration! Please see our [contributing guidelines](../CONTRIBUTING.md) for more information.

## Support

For issues or questions about the MCP Agent integration:
- Open an issue on [GitHub](https://github.com/AgentOps-AI/agentops/issues)
- Check the [AgentOps documentation](https://docs.agentops.ai)
- Join our [Discord community](https://discord.gg/agentops)