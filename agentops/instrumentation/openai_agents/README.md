# OpenAI Agents SDK Instrumentation

This module provides automatic instrumentation for the OpenAI Agents SDK, adding telemetry that follows OpenTelemetry semantic conventions for Generative AI systems.

## Architecture Overview

The OpenAI Agents SDK instrumentor works by:

1. Intercepting the Agents SDK's trace processor interface to capture Agent, Function, Generation, and other span types
2. Monkey-patching the Agents SDK `Runner` class to capture the full execution lifecycle, including streaming operations
3. Converting all captured data to OpenTelemetry spans and metrics following semantic conventions

## Span Types

The instrumentor captures the following span types:

- **Trace**: The root span representing an entire agent workflow execution
  - Implementation: `_export_trace()` method in `exporter.py`
  - Creates a span with the trace name, ID, and workflow metadata

- **Agent**: Represents an agent's execution lifecycle
  - Implementation: `_process_agent_span()` method in `exporter.py`
  - Uses `SpanKind.CONSUMER` to indicate an agent receiving a request
  - Captures agent name, input, output, tools, and other metadata

- **Function**: Represents a tool/function call
  - Implementation: `_process_function_span()` method in `exporter.py`
  - Uses `SpanKind.CLIENT` to indicate an outbound call to a function
  - Captures function name, input arguments, output results, and error information

- **Generation**: Captures details of model generation
  - Implementation: `_process_generation_span()` method in `exporter.py`
  - Uses `SpanKind.CLIENT` to indicate an outbound call to an LLM
  - Captures model name, configuration, usage statistics, and response content

- **Response**: Lightweight span for tracking model response IDs
  - Implementation: Handled within `_process_response_api()` and `_process_completions()` methods
  - Extracts response IDs and metadata from both Chat Completion API and Response API formats

- **Handoff**: Represents control transfer between agents
  - Implementation: Captured through the `AgentAttributes.HANDOFFS` attribute
  - Maps from the Agents SDK's "handoffs" field to standardized attribute name

## Metrics

The instrumentor collects the following metrics:

- **Agent Runs**: Number of agent runs
  - Implementation: `_agent_run_counter` in `instrumentor.py`
  - Incremented at the start of each agent run with metadata about the agent and run configuration

- **Agent Turns**: Number of agent turns
  - Implementation: Inferred from raw responses processing
  - Each raw response represents a turn in the conversation

- **Agent Execution Time**: Time taken for agent execution
  - Implementation: `_agent_execution_time_histogram` in `instrumentor.py`
  - Measured from the start of an agent run to its completion

- **Token Usage**: Number of input and output tokens used
  - Implementation: `_agent_token_usage_histogram` in `instrumentor.py`
  - Records both prompt and completion tokens separately with appropriate labels

## Key Design Patterns

### Target → Source Mapping Pattern

We use a consistent pattern for attribute mapping where dictionary keys represent the target attribute names (what we want in the final span), and values represent the source field names (where the data comes from):

```python
# Example from exporter.py
field_mapping = {
    AgentAttributes.AGENT_NAME: "name",     # target → source
    WorkflowAttributes.WORKFLOW_INPUT: "input",
    # ...
}
```

This pattern makes it easy to maintain mappings and apply them consistently.

### Multi-API Format Support

The instrumentor handles both OpenAI API formats:

1. **Chat Completion API**: Traditional format with "choices" array and prompt_tokens/completion_tokens
2. **Response API**: Newer format with "output" array and input_tokens/output_tokens

The implementation intelligently detects which format is being used and processes accordingly.

### Extended Token Mapping

We support both naming conventions for token metrics, following our consistent target→source pattern:

```python
TOKEN_USAGE_EXTENDED_MAPPING = {
    # Target semantic convention → source field
    SpanAttributes.LLM_USAGE_PROMPT_TOKENS: "input_tokens",
    SpanAttributes.LLM_USAGE_COMPLETION_TOKENS: "output_tokens",
}
```

### Streaming Operation Tracking

When instrumenting streaming operations, we:

1. Track active streaming operations using unique IDs
2. Handle proper flushing of spans to ensure metrics are recorded
3. Create separate spans for token usage metrics to avoid premature span closure

## Gotchas and Special Considerations

### Span Closure in Streaming Operations

Streaming operations in async contexts require special handling to avoid premature span closure. We use dedicated usage spans for streaming operations and maintain a tracking set of active stream IDs.

### Response API Content Extraction

The Response API has a nested structure for content:

```
output → message → content → [items] → text
```

Extracting the actual text requires special handling:

```python
# From _process_response_api in exporter.py
if isinstance(content_items, list):
    # Combine text from all text items
    texts = []
    for content_item in content_items:
        if content_item.get("type") == "output_text" and "text" in content_item:
            texts.append(content_item["text"])
    
    # Join texts (even if empty)
    attributes[f"{prefix}.content"] = " ".join(texts)
```

### Normalized Model Configuration

Model configuration parameters are normalized using a standard target→source mapping:

```python
MODEL_CONFIG_MAPPING = {
    # Target semantic convention → source field
    SpanAttributes.LLM_REQUEST_TEMPERATURE: "temperature",
    SpanAttributes.LLM_REQUEST_TOP_P: "top_p",
    SpanAttributes.LLM_REQUEST_FREQUENCY_PENALTY: "frequency_penalty",
    # ...
}
```

This ensures consistent attribute names regardless of source format, while maintaining our standard pattern where dictionary keys are always target attributes and values are source fields.

## Implementation Details

The instrumentor processes Agents SDK objects by extracting attributes using a standard mapping pattern, with attribute extraction based on the object's properties.

The implementation handles both Agents SDK object formats and serializes complex data appropriately when needed.

## TODO
- Add support for additional semantic conventions
    - `gen_ai` doesn't have conventions for response data beyond `role` and `content`