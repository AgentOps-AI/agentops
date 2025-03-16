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

## Trace Context Propagation

Our implementation uses OpenTelemetry's context propagation mechanism to ensure proper parent-child relationships between spans, maintaining a consistent trace ID across all spans from the same logical trace:

1. **Context Storage and Retrieval** for explicit context propagation:
   ```python
   # Store span contexts with explicit IDs
   self._span_contexts = {}  # span_id -> OpenTelemetry SpanContext object
   self._trace_root_contexts = {}  # trace_id -> OpenTelemetry Context object for the root span
   
   # When a root span is created for a trace
   if attributes.get("agentops.is_root_span") == "true" and trace_id:
       self._trace_root_contexts[trace_id] = trace.set_span_in_context(span)
       logger.debug(f"Stored root context for trace {trace_id}")
   ```

2. **Parent Context Resolution** for proper hierarchy:
   ```python
   def _get_parent_context(self, parent_id, trace_id):
       """Get the parent context for a span based on parent ID or trace ID."""
       # First try to find the direct parent context
       if parent_id and parent_id in self._span_contexts:
           parent_context = self._span_contexts[parent_id]
           return parent_context
           
       # If no direct parent found but we have a trace, use the trace's root context
       if trace_id and trace_id in self._trace_root_contexts:
           root_context = self._trace_root_contexts[trace_id]
           return root_context
           
       # Fall back to current context
       return context_api.get_current()
   ```

3. **Context-Aware Span Creation** using OpenTelemetry's context API:
   ```python
   # Create the span with explicit parent context
   with self.tracer.start_as_current_span(
       name=name,
       kind=kind,
       attributes=attributes,
       context=parent_context  # Explicitly passing parent context
   ) as span:
       # Store context for future child spans
       self._span_contexts[span_id] = trace.set_span_in_context(span)
   ```

4. **Trace Context Verification** to ensure spans maintain the same trace ID:
   ```python
   # Check if this span has the same trace ID as its root trace
   if trace_id in self._active_traces and 'otel_trace_id' in self._active_traces[trace_id]:
       root_trace_id = self._active_traces[trace_id]['otel_trace_id']
       if otel_trace_id == root_trace_id:
           logger.debug(f"Span {span_id} successfully linked to trace {trace_id}")
       else:
           logger.warning(f"Span {span_id} has different trace ID than root trace")
   ```

5. **Original IDs in Attributes** for query and correlation:
   ```python
   # Add trace/parent relationship attributes
   attributes.update({
       "agentops.original_trace_id": trace_id,
       "agentops.original_span_id": span_id,
   })
   
   if parent_id:
       attributes["agentops.parent_span_id"] = parent_id
   else:
       attributes["agentops.is_root_span"] = "true"
   ```

6. **Semantic Conventions** for LLM attributes:
   ```python
   # Using MessageAttributes for structured completion
   attributes[MessageAttributes.COMPLETION_CONTENT.format(i=0)] = safe_serialize(output)
   attributes[MessageAttributes.COMPLETION_ROLE.format(i=0)] = "assistant"
   ```

This approach ensures that:

1. All spans from the same logical trace share the same OpenTelemetry trace ID
2. Parent-child relationships are properly established in the trace context
3. The original trace and span IDs from the Agents SDK are preserved in attributes
4. Spans can be properly displayed in waterfall visualizations with correct hierarchy
5. Even when callbacks occur in different execution contexts, trace continuity is maintained

## Span Lifecycle Management

The lifecycle of spans is managed following this flow:

```
on_trace_start:
  ├── Create trace span with start_as_current_span
  ├── Store span in _active_spans for future reference
  └── Store OTel trace ID for debugging

on_span_start:
  ├── Build attributes based on span type
  ├── Add original trace/span ID and parent relationships
  ├── Create span with create_span context manager
  └── Store span in _active_spans dictionary

on_span_end:
  ├── Process metrics if needed
  └── Clean up span reference from _active_spans
  (The span is ended automatically when exiting the context manager)

on_trace_end:
  ├── Record execution time metrics
  ├── Create a final trace end span
  └── Clean up trace references
```

Using this context manager approach:
1. OpenTelemetry automatically handles span context propagation
2. Parent-child relationships are properly preserved
3. Spans are automatically ended when the context manager exits
4. The original Agents SDK trace and span IDs are preserved in attributes
5. Implementation is simpler and follows OpenTelemetry best practices