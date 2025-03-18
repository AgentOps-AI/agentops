# OpenTelemetry Implementation Notes

This document outlines best practices and implementation details for OpenTelemetry in AgentOps instrumentations.

## Key Concepts

### Context Propagation

OpenTelemetry relies on proper context propagation to maintain parent-child relationships between spans. This is essential for:

- Creating accurate trace waterfalls in visualizations
- Ensuring all spans from the same logical operation share a trace ID
- Allowing proper querying and filtering of related operations

### Core Patterns

When implementing instrumentations that need to maintain context across different execution contexts:

1. **Store span contexts in dictionaries:**
   ```python
   # Use weakref dictionaries to avoid memory leaks
   self._span_contexts = weakref.WeakKeyDictionary()
   self._trace_root_contexts = weakref.WeakKeyDictionary()
   ```

2. **Create spans with explicit parent contexts:**
   ```python
   parent_context = self._get_parent_context(trace_obj)
   with trace.start_as_current_span(
       name=span_name,
       context=parent_context,
       kind=trace.SpanKind.CLIENT,
       attributes=attributes,
   ) as span:
       # Span operations here
       # Store the span's context for future reference
       context = trace.set_span_in_context(span)
       self._span_contexts[span_obj] = context
   ```

3. **Implement helper methods to retrieve appropriate parent contexts:**
   ```python
   def _get_parent_context(self, trace_obj):
       # Try to get the trace's root context if it exists
       if trace_obj in self._trace_root_contexts:
           return self._trace_root_contexts[trace_obj]
       
       # Otherwise, use the current context
       return context_api.context.get_current()
   ```

4. **Debug trace continuity:**
   ```python
   current_span = trace.get_current_span()
   span_context = current_span.get_span_context()
   trace_id = format_trace_id(span_context.trace_id)
   logging.debug(f"Current span trace ID: {trace_id}")
   ```

## Common Pitfalls

1. **Naming conflicts:** Avoid using `trace` as a parameter name when you're also importing the OpenTelemetry `trace` module
   ```python
   # Bad
   def on_trace_start(self, trace):
       # This will cause conflicts with the imported trace module
   
   # Good
   def on_trace_start(self, trace_obj):
       # No conflicts with OpenTelemetry's trace module
   ```

2. **Missing parent contexts:** Always explicitly provide parent contexts when available, don't rely on current context alone

3. **Memory leaks:** Use `weakref.WeakKeyDictionary()` for storing spans to allow garbage collection

4. **Lost context:** When calling async or callback functions, be sure to preserve and pass the context

## Testing Context Propagation

To verify proper context propagation:

1. Enable debug logging for trace IDs
2. Run a simple end-to-end test that generates multiple spans
3. Verify all spans share the same trace ID
4. Check that parent-child relationships are correctly established

```python
# Example debug logging
logging.debug(f"Span {span.name} has trace ID: {format_trace_id(span.get_span_context().trace_id)}")
```

## Timestamp Handling in OpenTelemetry

When working with OpenTelemetry spans and timestamps:

1. **Automatic Timestamp Tracking:** OpenTelemetry automatically tracks timestamps for spans. When a span is created with `tracer.start_span()` or `tracer.start_as_current_span()`, the start time is captured automatically. When `span.end()` is called, the end time is recorded.

2. **No Manual Timestamp Setting Required:** The standard instrumentation pattern does not require manually setting timestamp attributes on spans. Instead, OpenTelemetry handles this internally through the SpanProcessor and Exporter classes.

3. **Timestamp Representation:** In the OpenTelemetry data model, timestamps are stored as nanoseconds since the Unix epoch (January 1, 1970).

4. **Serialization Responsibility:** The serialization of timestamps from OTel spans to output formats like JSON is handled by the Exporter components. If timestamps aren't appearing correctly in output APIs, the issue is likely in the API exporter, not in the span creation code.

5. **Debugging Timestamps:** To debug timestamp issues, verify that spans are properly starting and ending, rather than manually setting timestamp attributes:

```python
# Good pattern - timestamps handled by OpenTelemetry automatically
with tracer.start_as_current_span("my_operation") as span:
    # Do work
    pass  # span.end() is called automatically
```

Note: If timestamps are missing in API output (e.g., empty "start_time" fields), focus on fixes in the exporter and serialization layer, not by manually tracking timestamps in instrumentation code.

## Attributes in OpenTelemetry

When working with span attributes in OpenTelemetry:

1. **Root Attributes Node:** The root `attributes` object in the API output JSON should always be empty. This is by design. All attribute data should be stored in the `span_attributes` object.

2. **Span Attributes:** The `span_attributes` object is where all user-defined and semantic attribute data should be stored. This allows for a structured, hierarchical representation of attributes.

3. **Structure Difference:** While the root `attributes` appears as an empty object in the API output, this is normal and expected. Do not attempt to populate this object directly or duplicate data from `span_attributes` into it.

4. **Setting Attributes:** Always set span attributes using the semantic conventions defined in the `agentops/semconv` module:

```python
from agentops.semconv import agent

# Good pattern - using semantic conventions
span.set_attribute(agent.AGENT_NAME, "My Agent")
```