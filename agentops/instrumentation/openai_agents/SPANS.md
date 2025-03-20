# OpenAI Agents Spans and Traces

This document describes the span types, naming conventions, and attribute patterns used by the AgentOps instrumentation for the OpenAI Agents SDK.

## Span Types and Classes

The instrumentation works with these specific span data classes:

1. **AgentSpanData**: Represents a single agent's operation
   - Has attributes for name, input, output, tools, and handoffs
   - Processed by `get_agent_span_attributes()` using `AGENT_SPAN_ATTRIBUTES` mapping

2. **FunctionSpanData**: Represents tool or function calls
   - Has attributes for name, input, output, and from_agent
   - Processed by `get_function_span_attributes()` using `FUNCTION_SPAN_ATTRIBUTES` mapping

3. **GenerationSpanData**: Represents LLM model invocations
   - Has attributes for model, input, output, tools, and from_agent
   - Processed by `get_generation_span_attributes()` using `GENERATION_SPAN_ATTRIBUTES` mapping

4. **HandoffSpanData**: Represents agent-to-agent handoffs
   - Has attributes for from_agent and to_agent
   - Processed by `get_handoff_span_attributes()` using `HANDOFF_SPAN_ATTRIBUTES` mapping

5. **ResponseSpanData**: Represents model response data
   - Has attributes for input and response
   - Processed by `get_response_span_attributes()` using `RESPONSE_SPAN_ATTRIBUTES` mapping

## Span Naming Conventions

Spans are named according to these conventions:

1. **Trace Spans**: `agents.trace.{workflow_name}`
   - Represents the entire agent workflow
   - Named after the workflow or trace name

2. **Agent Spans**: `agents.agent`
   - Represents a single agent's operation
   - Uses `SpanKind.CONSUMER`

3. **Function Spans**: `agents.function`
   - Represents tool or function calls
   - Uses `SpanKind.CLIENT`

4. **Generation Spans**: `agents.generation`
   - Represents LLM model invocations
   - Uses `SpanKind.CLIENT`

5. **Handoff Spans**: `agents.handoff`
   - Represents agent-to-agent handoffs
   - Uses `SpanKind.INTERNAL`

6. **Response Spans**: `agents.response`
   - Represents model response data
   - Uses `SpanKind.CLIENT`

## Span Hierarchy

The spans follow a parent-child relationship that reflects the execution flow:

```
agents.trace.{workflow_name}
  └── agents.agent
      ├── agents.generation
      ├── agents.function
      ├── agents.response
      └── agents.handoff
```

## Semantic Conventions and Attributes

Each span type has attributes following OpenTelemetry semantic conventions:

### Common Attributes (All Spans)

- `trace.id`: OpenTelemetry trace ID
- `span.id`: OpenTelemetry span ID
- `parent.id`: Parent span ID (if applicable)
- `instrumentation.name`: "agentops"
- `instrumentation.version`: AgentOps library version
- `instrumentation.library.name`: "openai_agents"
- `instrumentation.library.version`: Library version

### Workflow and Trace Attributes

- `workflow.name`: Name of the workflow or trace
- `workflow.step_type`: "trace" for trace spans
- `workflow.input`: Input to the workflow
- `workflow.final_output`: Final output from the workflow

### Agent Attributes

- `agent.name`: The name of the agent
- `agent.tools`: Comma-separated list of available tools
- `agent.handoffs`: Comma-separated list of handoff targets
- `agent.from`: Source agent in handoffs (used in HandoffSpanData)
- `agent.to`: Destination agent in handoffs (used in HandoffSpanData)

### LLM Attributes

- `gen_ai.system`: "openai" for all OpenAI spans
- `gen_ai.request.model`: Model used for generation
- `gen_ai.response.model`: Model that provided the response
- `gen_ai.prompt`: Input prompt or message
- `gen_ai.completion.0.role`: Role of the completion message (usually "assistant")
- `gen_ai.completion.0.content`: Content of the completion message
- `gen_ai.tool_call.0.0.name`: Name of the tool called (if applicable)
- `gen_ai.tool_call.0.0.arguments`: Arguments for the tool call (if applicable)

### Token Usage Attributes

- `gen_ai.usage.prompt_tokens`: Number of input tokens
- `gen_ai.usage.completion_tokens`: Number of output tokens
- `gen_ai.usage.total_tokens`: Total number of tokens
- `gen_ai.usage.reasoning_tokens`: Tokens used for reasoning (Response API)
- `gen_ai.usage.cache_read.input_tokens`: Cached input tokens (Response API)

## Span Lifecycle Management

The exporter handles span lifecycle with these stages:

1. **Start Events**:
   - Create spans with `start_span()` (not using context manager)
   - Store span references in tracking dictionaries
   - Leave status as UNSET to indicate in-progress

2. **End Events**:
   - Look up existing span by ID
   - Update with final attributes
   - Set appropriate status and end the span manually

3. **Error Handling**:
   - Set status to ERROR for spans with errors
   - Add error type and message as attributes
   - Record exceptions with `record_exception()`

## OpenTelemetry Span Kinds

Span kinds map to OpenTelemetry concepts:

- `AgentSpanData` → `SpanKind.CONSUMER`
- `FunctionSpanData` → `SpanKind.CLIENT`
- `GenerationSpanData` → `SpanKind.CLIENT`
- `ResponseSpanData` → `SpanKind.CLIENT`
- `HandoffSpanData` → `SpanKind.INTERNAL`