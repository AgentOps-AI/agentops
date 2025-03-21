# OpenAI Agents Tracing API Integration

This document provides an overview of how AgentOps integrates with the OpenAI Agents SDK tracing system.

## OpenAI Agents Tracing API Overview

The OpenAI Agents SDK provides a comprehensive tracing system that allows you to monitor and instrument agent activities. AgentOps integrates with this system to capture and forward trace data to its backend.

## Core Integration Methods

### 1. `add_trace_processor(processor)`

The main integration point that allows external systems like AgentOps to receive trace events:

```python
from agents import add_trace_processor
from agentops.instrumentation.openai_agents.processor import OpenAIAgentsProcessor

processor = OpenAIAgentsProcessor()
add_trace_processor(processor)
```

### 2. `set_trace_processors(processors)`

Replaces all current processors with a new list:

```python
from agents import set_trace_processors
set_trace_processors([my_processor1, my_processor2])
```

### 3. `set_tracing_disabled(disabled)`

Globally enables/disables tracing:

```python
from agents import set_tracing_disabled
set_tracing_disabled(True)  # Disable tracing
```

### 4. `set_tracing_export_api_key(api_key)`

Sets the API key for the backend exporter:

```python
from agents import set_tracing_export_api_key
set_tracing_export_api_key("your-api-key")
```

## Span Creation Methods

The SDK provides specialized methods for creating different types of spans:

1. **`agent_span(name, handoffs, tools, output_type, ...)`**
   - Creates spans for agent operations
   - Tracks agent name, available tools, potential handoffs

2. **`function_span(name, input, output, ...)`**
   - Creates spans for function/tool calls
   - Records function name, input arguments, and results

3. **`generation_span(input, output, model, model_config, usage, ...)`**
   - Creates spans for LLM generations
   - Records prompts, completions, model details, and token usage

4. **`response_span(response, ...)`**
   - Lightweight span for capturing OpenAI API response metadata

5. **`handoff_span(from_agent, to_agent, ...)`**
   - Tracks agent-to-agent handoffs

6. **`guardrail_span(name, triggered, ...)`**
   - Records guardrail evaluations

7. **`custom_span(name, data, ...)`**
   - Creates user-defined spans with arbitrary data

## Trace and Context Management

1. **`trace(workflow_name, trace_id, group_id, metadata, ...)`**
   - Creates and manages a trace context
   - Groups related spans into a logical trace/session

2. **`get_current_span()`**
   - Returns the current active span

3. **`get_current_trace()`**
   - Returns the current active trace

## How AgentOps Implements Integration

AgentOps integrates with this API through:

1. The `OpenAIAgentsProcessor` class that implements the `TracingProcessor` interface
2. The `create_span` context manager that ensures proper parent-child relationships between spans
3. The `AgentsInstrumentor` which registers the processor and adds additional instrumentation

This integration allows AgentOps to capture detailed information about agent execution, including:
- Agent operations and tool usage
- LLM requests and responses 
- Token usage metrics
- Error information
- Agent-to-agent handoffs

### Trace Context Propagation

Our implementation ensures proper parent-child relationships between spans through:

1. **Context Manager Pattern**: Using `start_as_current_span()` to maintain the OpenTelemetry span context
2. **Parent Reference Tracking**: Storing parent span relationships and using them to create proper span hierarchies
3. **Trace Correlation Attributes**: Adding consistent attributes to help with querying:
   - `agentops.original_trace_id`: Original trace ID from the Agents SDK
   - `agentops.original_span_id`: Original span ID from the Agents SDK
   - `agentops.parent_span_id`: Parent span ID for child spans
   - `agentops.trace_hash`: Consistent hash based on the original trace ID
   - `agentops.is_root_span`: "true" for spans without a parent

When querying spans for analysis:
1. Group spans by `agentops.original_trace_id` to find all spans in the same trace
2. Use `agentops.parent_span_id` to reconstruct the parent-child hierarchy

## Span Data Types

Several specialized span data types exist in the OpenAI Agents SDK to capture different operations:

- **AgentSpanData**: Captures agent execution data
- **FunctionSpanData**: Records tool/function calls
- **GenerationSpanData**: Records LLM generation details
- **ResponseSpanData**: Captures model response information
- **HandoffSpanData**: Tracks agent-to-agent handoffs
- **GuardrailSpanData**: Records guardrail evaluations
- **CustomSpanData**: For user-defined spans

## Processor Interface

The `TracingProcessor` interface defines methods processors must implement:
- `on_trace_start`: Called when a trace begins
- `on_trace_end`: Called when a trace ends
- `on_span_start`: Called when a span begins
- `on_span_end`: Called when a span completes
- `shutdown`: Called during application shutdown
- `force_flush`: Forces immediate processing of pending spans

The processor receives events from OpenAI Agents SDK's tracing system through these callback methods, translates them to OpenTelemetry spans, and sends them to the AgentOps backend for analysis and visualization.