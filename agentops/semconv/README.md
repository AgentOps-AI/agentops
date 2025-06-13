# OpenTelemetry Semantic Conventions for AgentOps

This module defines semantic conventions for observability data in AgentOps, following OpenTelemetry standards where applicable.

## Overview

The semantic conventions are organized into the following modules:

- **`core`** - Core attributes for errors, tags, and trace context
- **`span_attributes`** - LLM and GenAI-specific span attributes
- **`agent`** - Agent-specific attributes (identity, capabilities, interactions)
- **`tool`** - Tool/function call attributes
- **`workflow`** - Workflow and session attributes
- **`message`** - Message and conversation attributes
- **`instrumentation`** - Instrumentation metadata
- **`resource`** - Resource and environment attributes
- **`langchain`** - LangChain-specific attributes
- **`meters`** - Metric names and definitions
- **`span_kinds`** - Span kind enumerations
- **`status`** - Status enumerations (e.g., tool execution status)

## Usage

Import the attributes you need:

```python
from agentops.semconv import (
    SpanAttributes,
    AgentAttributes,
    ToolAttributes,
    WorkflowAttributes,
    CoreAttributes,
    MessageAttributes
)

# Set span attributes
span.set_attribute(SpanAttributes.LLM_REQUEST_MODEL, "gpt-4")
span.set_attribute(AgentAttributes.AGENT_NAME, "assistant")
span.set_attribute(ToolAttributes.TOOL_NAME, "web_search")
```

## Key Conventions

### Core Attributes
- **Error handling**: `error.type`, `error.message`
- **Trace context**: `trace.id`, `span.id`, `parent.id`
- **Tags**: `agentops.tags`

### LLM/GenAI Attributes
Following OpenTelemetry GenAI conventions:
- **Request**: `gen_ai.request.*` (model, temperature, max_tokens, etc.)
- **Response**: `gen_ai.response.*` (model, id, finish_reason)
- **Usage**: `gen_ai.usage.*` (prompt_tokens, completion_tokens, total_tokens)
- **Messages**: `gen_ai.prompt.*`, `gen_ai.completion.*`

### Agent Attributes
- **Identity**: `agent.id`, `agent.name`, `agent.role`
- **Capabilities**: `agent.tools`, `agent.models`
- **Interactions**: `from_agent`, `to_agent`

### Tool Attributes
- **Identity**: `tool.name`, `tool.description`
- **Execution**: `tool.parameters`, `tool.result`, `tool.status`

### Workflow Attributes
- **Workflow**: `workflow.name`, `workflow.type`, `workflow.id`
- **I/O**: `workflow.input`, `workflow.output`
- **Session**: `workflow.session_id`, `workflow.user_id`

## Message Conventions

Messages use indexed attributes for handling multiple messages:
- `gen_ai.prompt.{i}.role` - Role of prompt at index i
- `gen_ai.prompt.{i}.content` - Content of prompt at index i
- `gen_ai.completion.{i}.content` - Completion content at index i
- `gen_ai.completion.{i}.tool_calls.{j}.name` - Tool call j in completion i

## Recent Changes

### Cleanup (v2.0)
- Removed unused attributes: `IN_FLIGHT`, `EXPORT_IMMEDIATELY`, `PARENT_SPAN_ID`, `PARENT_TRACE_ID`, `PARENT_SPAN_KIND`, `PARENT_SPAN_NAME`, `LLM_OPENAI_API_TYPE`
- Consolidated redundant attributes
- Aligned with OpenTelemetry GenAI semantic conventions
- Improved documentation and examples

### Best Practices
1. **Use standard conventions**: Prefer OpenTelemetry standard attributes over custom ones
2. **Consistent naming**: Follow the established patterns (e.g., `gen_ai.*` for LLM attributes)
3. **Avoid duplication**: Don't create new attributes if existing ones serve the purpose
4. **Document deviations**: Note when attributes deviate from OpenTelemetry standards

## Contributing

When adding new attributes:
1. Check if OpenTelemetry already defines a suitable convention
2. Follow the naming patterns established in each module
3. Add documentation explaining the attribute's purpose
4. Update this README if adding new categories

## References

- [OpenTelemetry Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/)
- [OpenTelemetry GenAI Semantic Conventions](https://github.com/open-telemetry/semantic-conventions/blob/main/docs/gen-ai/gen-ai-spans.md)