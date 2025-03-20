# OpenAI Agents SDK Instrumentation

This module provides automatic instrumentation for the OpenAI Agents SDK, adding telemetry that follows OpenTelemetry semantic conventions for Generative AI systems.

## Architecture Overview

The OpenAI Agents SDK instrumentor works by:

1. Intercepting the Agents SDK's trace processor interface to capture Agent, Function, Generation, and other span types
2. Monkey-patching the Agents SDK `Runner` class to capture the full execution lifecycle, including streaming operations
3. Converting all captured data to OpenTelemetry spans and metrics following semantic conventions

The instrumentation is organized into several key components:

1. **Instrumentor (`instrumentor.py`)**: The entry point that patches the Agents SDK and configures trace capture
2. **Processor (`processor.py`)**: Receives events from the SDK and prepares them for export
3. **Exporter (`exporter.py`)**: Converts SDK spans to OpenTelemetry spans and exports them
4. **Attributes Module (`attributes/`)**: Specialized modules for extracting and formatting span attributes

## Attribute Processing Modules

The attribute modules extract and format OpenTelemetry-compatible attributes from span data:

- **Common (`attributes/common.py`)**: Core attribute extraction functions for all span types and utility functions
- **Completion (`attributes/completion.py`)**: Handles different completion content formats (Chat Completions API, Response API, Agents SDK) 
- **Model (`attributes/model.py`)**: Extracts model information and parameters
- **Tokens (`attributes/tokens.py`)**: Processes token usage data and metrics

Each getter function in these modules is focused on a single responsibility and does not modify global state. Functions are designed to be composable, allowing different attribute types to be combined as needed in the exporter.

## Span Types

The instrumentor captures the following span types:

- **Trace**: The root span representing an entire agent workflow execution
  - Created using `get_base_trace_attributes()` to initialize with standard fields
  - Captures workflow name, trace ID, and workflow-level metadata

- **Agent**: Represents an agent's execution lifecycle
  - Processed using `get_agent_span_attributes()` with `AGENT_SPAN_ATTRIBUTES` mapping
  - Uses `SpanKind.CONSUMER` to indicate an agent receiving a request
  - Captures agent name, input, output, tools, and other metadata

- **Function**: Represents a tool/function call
  - Processed using `get_function_span_attributes()` with `FUNCTION_SPAN_ATTRIBUTES` mapping
  - Uses `SpanKind.CLIENT` to indicate an outbound call to a function
  - Captures function name, input arguments, output results, and from_agent information

- **Generation**: Captures details of model generation
  - Processed using `get_generation_span_attributes()` with `GENERATION_SPAN_ATTRIBUTES` mapping
  - Uses `SpanKind.CLIENT` to indicate an outbound call to an LLM
  - Captures model name, configuration, usage statistics, and response content

- **Response**: Lightweight span for tracking model response data
  - Processed using `get_response_span_attributes()` with `RESPONSE_SPAN_ATTRIBUTES` mapping
  - Extracts response content and metadata from different API formats

- **Handoff**: Represents control transfer between agents
  - Processed using `get_handoff_span_attributes()` with `HANDOFF_SPAN_ATTRIBUTES` mapping
  - Tracks from_agent and to_agent information

## Span Lifecycle Management

The exporter (`exporter.py`) handles the full span lifecycle:

1. **Start Events**:
   - Create spans but DO NOT END them
   - Store span references in tracking dictionaries
   - Use OpenTelemetry's start_span to control when spans end
   - Leave status as UNSET to indicate in-progress

2. **End Events**:
   - Look up existing span by ID in tracking dictionaries
   - If found and not ended:
     - Update span with all final attributes
     - Set status to OK or ERROR based on task outcome
     - End the span manually
   - If not found or already ended:
     - Create a new complete span with all data
     - End it immediately

3. **Error Handling**:
   - Check if spans are already ended before attempting updates
   - Provide informative log messages about span lifecycle
   - Properly clean up tracking resources

## Key Design Patterns

### Semantic Conventions

All attribute names follow the OpenTelemetry semantic conventions defined in `agentops.semconv`:

```python
# Using constants from semconv module
attributes[CoreAttributes.TRACE_ID] = trace_id
attributes[WorkflowAttributes.WORKFLOW_NAME] = trace.name
attributes[SpanAttributes.LLM_SYSTEM] = "openai"
attributes[MessageAttributes.COMPLETION_CONTENT.format(i=0)] = content
```

### Target → Source Attribute Mapping

We use a consistent pattern for attribute extraction with typed mapping dictionaries:

```python
# Attribute mapping example
AGENT_SPAN_ATTRIBUTES: AttributeMap = {
    # target_attribute: source_attribute
    AgentAttributes.AGENT_NAME: "name",
    WorkflowAttributes.WORKFLOW_INPUT: "input",
    WorkflowAttributes.FINAL_OUTPUT: "output",
    # ...
}
```
