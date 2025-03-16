# OpenTelemetry Context Propagation

This document outlines best practices and implementation details for OpenTelemetry context propagation in AgentOps instrumentations.

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