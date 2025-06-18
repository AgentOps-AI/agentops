# OpenTelemetry Semantic Conventions for Generative AI Systems

This module provides semantic conventions for telemetry data in AI and LLM systems, following OpenTelemetry GenAI conventions where applicable.

## Core Conventions

### Agent Attributes (`agent.py`)
```python
from agentops.semconv import AgentAttributes

AgentAttributes.AGENT_NAME     # Agent name
AgentAttributes.AGENT_ROLE     # Agent role/type
AgentAttributes.AGENT_ID       # Unique agent identifier
```

### Tool Attributes (`tool.py`)
```python
from agentops.semconv import ToolAttributes, ToolStatus

ToolAttributes.TOOL_NAME        # Tool name
ToolAttributes.TOOL_PARAMETERS  # Tool input parameters
ToolAttributes.TOOL_RESULT      # Tool execution result
ToolAttributes.TOOL_STATUS      # Tool execution status

# Tool status values
ToolStatus.EXECUTING   # Tool is executing
ToolStatus.SUCCEEDED   # Tool completed successfully
ToolStatus.FAILED      # Tool execution failed
```

### Workflow Attributes (`workflow.py`)
```python
from agentops.semconv import WorkflowAttributes

WorkflowAttributes.WORKFLOW_NAME      # Workflow name
WorkflowAttributes.WORKFLOW_TYPE      # Workflow type
WorkflowAttributes.WORKFLOW_STEP_NAME # Step name
WorkflowAttributes.WORKFLOW_STEP_STATUS # Step status
```

### LLM/GenAI Attributes (`span_attributes.py`)
Following OpenTelemetry GenAI conventions:

```python
from agentops.semconv import SpanAttributes

# Request attributes
SpanAttributes.LLM_REQUEST_MODEL        # Model name (e.g., "gpt-4")
SpanAttributes.LLM_REQUEST_TEMPERATURE  # Temperature setting
SpanAttributes.LLM_REQUEST_MAX_TOKENS   # Max tokens to generate

# Response attributes  
SpanAttributes.LLM_RESPONSE_MODEL       # Model that generated response
SpanAttributes.LLM_RESPONSE_FINISH_REASON # Why generation stopped

# Token usage
SpanAttributes.LLM_USAGE_PROMPT_TOKENS     # Input tokens
SpanAttributes.LLM_USAGE_COMPLETION_TOKENS # Output tokens
SpanAttributes.LLM_USAGE_TOTAL_TOKENS      # Total tokens
```

### Message Attributes (`message.py`)
For chat-based interactions:

```python
from agentops.semconv import MessageAttributes

# Prompt messages (indexed)
MessageAttributes.PROMPT_ROLE.format(i=0)     # Role at index 0
MessageAttributes.PROMPT_CONTENT.format(i=0)  # Content at index 0

# Completion messages (indexed)
MessageAttributes.COMPLETION_ROLE.format(i=0)    # Role at index 0
MessageAttributes.COMPLETION_CONTENT.format(i=0) # Content at index 0

# Tool calls (indexed)
MessageAttributes.TOOL_CALL_NAME.format(i=0)      # Tool name
MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=0) # Tool arguments
```

### Core Attributes (`core.py`)
```python
from agentops.semconv import CoreAttributes

CoreAttributes.TRACE_ID    # Trace identifier
CoreAttributes.SPAN_ID     # Span identifier
CoreAttributes.PARENT_ID   # Parent span identifier
CoreAttributes.TAGS        # User-defined tags
```

## Usage Guidelines

1. **Follow OpenTelemetry conventions** - Use `gen_ai.*` prefixed attributes for LLM operations
2. **Use indexed attributes for collections** - Messages, tool calls, etc. should use `.format(i=index)`
3. **Prefer specific over generic** - Use `SpanAttributes.LLM_REQUEST_MODEL` over custom attributes
4. **Document custom attributes** - If you need provider-specific attributes, document them clearly

## Provider-Specific Conventions

### OpenAI
- `SpanAttributes.LLM_OPENAI_RESPONSE_SYSTEM_FINGERPRINT`
- `SpanAttributes.LLM_OPENAI_API_VERSION`

### LangChain  
- `LangChainAttributes.CHAIN_TYPE`
- `LangChainAttributes.TOOL_NAME`

## Metrics (`meters.py`)

Standard metrics for instrumentation:

```python
from agentops.semconv import Meters

Meters.LLM_TOKEN_USAGE         # Token usage histogram
Meters.LLM_OPERATION_DURATION  # Operation duration histogram
Meters.LLM_COMPLETIONS_EXCEPTIONS # Exception counter
```

## Best Practices

1. **Consistency** - Use the same attributes across instrumentations
2. **Completeness** - Capture essential attributes for debugging
3. **Performance** - Avoid capturing large payloads as attributes
4. **Privacy** - Be mindful of sensitive data in attributes