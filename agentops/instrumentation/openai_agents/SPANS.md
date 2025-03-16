# OpenAI Agents Spans and Traces

This document describes how AgentOps implements the OpenAI Agents Traces API, including span naming conventions, hierarchies, and search patterns.

## Span Naming Conventions

Our instrumentation follows these naming patterns:

1. **Trace Spans**: `agents.trace.{workflow_name}`
   - Represents the entire agent workflow
   - Named after the workflow or agent name

2. **Agent Spans**: `agents.agent.{agent_name}`
   - Represents a single agent's operation
   - Named after the agent's name

3. **Function Spans**: `agents.function.{function_name}`
   - Represents tool or function calls
   - Named after the function's name

4. **Generation Spans**: `agents.generation.{model_name}`
   - Represents LLM model invocations
   - Named after the model name when available

5. **Handoff Spans**: `agents.handoff.{from_agent}_to_{to_agent}`
   - Represents agent-to-agent handoffs
   - Named with both the origin and destination agents

6. **Response Spans**: `agents.response.{response_id}`
   - Lightweight spans for model responses
   - Named with response ID when available

7. **Streaming Operation Spans**: `agents.run_streamed.{agent_name}`
   - Special spans for streaming operations
   - Include `stream: true` attribute and unique `stream_id`

## Span Hierarchy

The spans follow a parent-child relationship that reflects the execution flow:

```
agents.trace.{workflow_name}
  └── agents.agent.{agent_name}
      ├── agents.generation.{model_name}
      ├── agents.function.{function_name}
      └── agents.handoff.{from_agent}_to_{to_agent}
```

For streaming operations, there's an additional usage span:

```
agents.run_streamed.{agent_name}
  └── agents.run_streamed.usage.{agent_name}
```

## Key Attributes for Finding Spans

To locate specific spans in traces and logs, use these key attributes:

1. **Agent Identification**:
   - `agent.name`: The name of the agent
   - `agent.from`: Source agent in handoffs
   - `agent.to`: Destination agent in handoffs

2. **Operation Type**:
   - `workflow.type`: Identifies the operation type (e.g., "agents.run_sync")
   - `workflow.step_type`: Distinguishes between trace, span, and other step types

3. **Streaming Operations**:
   - `stream`: "true" or "false" to identify streaming operations
   - `stream_id`: Unique identifier for correlating streaming events

4. **Model Information**:
   - `gen_ai.request.model`: The model used for generation
   - `gen_ai.response.model`: The model that provided the response (may differ)

5. **Execution Context**:
   - `trace.id`: OpenTelemetry trace ID
   - `span.id`: OpenTelemetry span ID
   - `parent.id`: Parent span ID for reconstructing hierarchies

## Metrics and Token Usage

Token usage is captured on spans with these attributes:

1. **Token Counters**:
   - `gen_ai.usage.prompt_tokens`: Input token count
   - `gen_ai.usage.completion_tokens`: Output token count
   - `gen_ai.usage.total_tokens`: Total token usage
   - `gen_ai.usage.reasoning_tokens`: Tokens used for reasoning (when available)

2. **Histograms**:
   - `gen_ai.operation.duration`: Duration of operations in seconds
   - `gen_ai.token_usage`: Token usage broken down by token type

## Searching and Filtering Examples

To find specific spans and analyze operations:

1. **Find all operations from a specific agent**:
   - Filter by `agent.name = "your_agent_name"`

2. **Find all streaming operations**:
   - Filter by `stream = "true"`

3. **Find all function calls**:
   - Filter by name prefix `agents.function`

4. **Find generation spans with a specific model**:
   - Filter by `gen_ai.request.model = "gpt-4-turbo"`

5. **Find spans with errors**:
   - Filter by `error.type IS NOT NULL`

## OpenTelemetry Compatibility

Our implementation bridges the OpenAI Agents tracing system with OpenTelemetry by:

1. Mapping Agents SDK span types to OpenTelemetry span kinds:
   - Agent spans → `SpanKind.CONSUMER`
   - Function/Generation spans → `SpanKind.CLIENT`
   - Trace spans → `SpanKind.INTERNAL`

2. Using semantic convention attributes from the OpenTelemetry AI conventions
   - All spans include the `service.name = "agentops.agents"` attribute
   - LLM-specific attributes use the `gen_ai.*` namespace

3. Preserving context for distributed tracing:
   - All spans include trace, span, and parent IDs
   - Follows W3C Trace Context specification