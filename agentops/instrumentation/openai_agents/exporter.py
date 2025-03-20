"""OpenAI Agents SDK Instrumentation Exporter for AgentOps

SPAN LIFECYCLE MANAGEMENT:
This implementation handles the span lifecycle across multiple callbacks with a precise approach:

1. Start Events:
   - Create spans but DO NOT END them
   - Store span references in tracking dictionaries
   - Use OpenTelemetry's start_span (not context manager) to control when spans end
   - Leave status as UNSET to indicate in-progress

2. End Events:
   - Look up existing span by ID in tracking dictionaries
   - If found and not ended:
     - Update span with all final attributes
     - Set status to OK or ERROR based on task outcome
     - End the span manually
   - If not found or already ended:
     - Create a new complete span with all data
     - End it immediately

3. Error Handling:
   - Check if spans are already ended before attempting updates
   - Provide informative log messages about span lifecycle
   - Properly clean up tracking resources

This approach is essential because:
- Agents SDK sends separate start and end events for each task
- We need to maintain a single span for the entire task lifecycle to get accurate timing
- Final data (outputs, token usage, etc.) is only available at the end event
- We want to avoid creating duplicate spans for the same task
- Spans must be properly created and ended to avoid leaks

The span lifecycle management ensures spans have:
- Accurate start and end times (preserving the actual task duration)
- Complete attribute data from both start and end events
- Proper status reflecting task completion
- All final outputs, errors, and metrics
- Clean resource management with no memory leaks

IMPORTANT SERIALIZATION RULES:
1. We do not serialize data structures arbitrarily; everything has a semantic convention.
2. Span attributes should use semantic conventions and avoid complex serialized structures.
3. Keep all string data in its original form - do not parse JSON within strings.
4. If a function has JSON attributes for its arguments, do not parse that JSON - keep as string.
5. If a completion or response body text/content contains JSON, keep it as a string.
6. When a semantic convention requires a value to be added to span attributes:
   - DO NOT apply JSON serialization
   - All attribute values should be strings or simple numeric/boolean values
   - If we encounter JSON or an object in an area that expects a string, raise an exception
7. Function arguments and tool call arguments should remain in their raw string form.

CRITICAL: NEVER MANUALLY SET THE ROOT COMPLETION ATTRIBUTES
- DO NOT set SpanAttributes.LLM_COMPLETIONS or "gen_ai.completion" manually
- Let OpenTelemetry backend derive these values from the detailed attributes
- Setting root completion attributes creates duplication and inconsistency

STRUCTURED ATTRIBUTE HANDLING:
- Always use MessageAttributes semantic conventions for content and tool calls
- For chat completions, use MessageAttributes.COMPLETION_CONTENT.format(i=0) 
- For tool calls, use MessageAttributes.TOOL_CALL_NAME.format(i=0, j=0), etc.
- Never try to combine or aggregate contents into a single attribute
- Each message component should have its own properly formatted attribute
- This ensures proper display in OpenTelemetry backends and dashboards

IMPORTANT FOR TESTING:
- Tests should verify attribute existence using MessageAttributes constants
- Do not check for the presence of SpanAttributes.LLM_COMPLETIONS
- Verify individual content/tool attributes instead of root attributes

WAYS TO USE SEMANTIC CONVENTIONS WHEN REFERENCING SPAN ATTRIBUTES:
1. Always use the constant values from the semantic convention classes rather than hardcoded strings:
   ```python
   # Good
   attributes[SpanAttributes.LLM_PROMPTS] = input_value
   
   # Avoid
   attributes["gen_ai.prompt"] = input_value
   ```

2. For structured attributes like completions, use the format methods from MessageAttributes:
   ```python
   # Good
   attributes[MessageAttributes.COMPLETION_CONTENT.format(i=0)] = content
   
   # Avoid
   attributes["gen_ai.completion.0.content"] = content
   ```

3. Be consistent with naming patterns across different span types:
   - Use `SpanAttributes.LLM_PROMPTS` for input/prompt data
   - Use `MessageAttributes.COMPLETION_CONTENT.format(i=0)` for output/response content
   - Use `WorkflowAttributes.FINAL_OUTPUT` for workflow outputs

4. Keep special attributes at their correct levels:
   - Don't manually set root completion attributes (`SpanAttributes.LLM_COMPLETIONS`) 
   - Set MessageAttributes for each individual message component
   - Let the OpenTelemetry backend derive the root attributes

5. When searching for attributes in spans, use the constants from the semantic convention classes:
   ```python
   # Good
   if SpanAttributes.LLM_PROMPTS in span.attributes:
       # Do something
   
   # Avoid
   if "gen_ai.prompt" in span.attributes:
       # Do something
   ```
"""
import json
from typing import Any, Dict, Optional

from opentelemetry import trace, context as context_api
from opentelemetry.trace import get_tracer, SpanKind, Status, StatusCode, NonRecordingSpan
from opentelemetry import trace as trace_api
from agentops.semconv import (
    CoreAttributes, 
    WorkflowAttributes,
    InstrumentationAttributes,
    AgentAttributes,
    SpanAttributes,
    MessageAttributes
)
from agentops.helpers.serialization import safe_serialize, model_to_dict

# Import directly from attribute modules
from agentops.instrumentation.openai_agents.attributes.tokens import process_token_usage, safe_parse
from agentops.instrumentation.openai_agents.attributes.common import (
    get_span_kind,
    get_base_trace_attributes,
    get_base_span_attributes,
    get_span_attributes,
    get_common_instrumentation_attributes
)
from agentops.instrumentation.openai_agents.attributes.model import (
    extract_model_config,
    get_model_info
)
from agentops.instrumentation.openai_agents.attributes.completion import get_generation_output_attributes

from agentops.logging import logger
from agentops.instrumentation.openai_agents import LIBRARY_NAME, LIBRARY_VERSION


TRACE_PREFIX = "agents.trace"


def log_otel_trace_id(span_type):
    """Log the OpenTelemetry trace ID for debugging and correlation purposes.
    
    The hexadecimal OTel trace ID is essential for querying the backend database 
    and correlating local debugging logs with server-side trace data. This ID 
    is different from the Agents SDK trace_id and is the primary key used in 
    observability systems and the AgentOps dashboard.
    
    This function retrieves the current OpenTelemetry trace ID directly from the
    active span context and formats it as a 32-character hex string.
    
    Args:
        span_type: The type of span being exported for logging context
        
    Returns:
        str or None: The OpenTelemetry trace ID as a hex string, or None if unavailable
    """
    current_span = trace.get_current_span()
    if hasattr(current_span, "get_span_context"):
        ctx = current_span.get_span_context()
        if hasattr(ctx, "trace_id") and ctx.trace_id:
            # Convert trace_id to 32-character hex string as shown in the API
            otel_trace_id = f"{ctx.trace_id:032x}" if isinstance(ctx.trace_id, int) else str(ctx.trace_id)
            logger.debug(f"[SPAN] Export | Type: {span_type} | TRACE ID: {otel_trace_id}")
            return otel_trace_id
    
    logger.debug(f"[SPAN] Export | Type: {span_type} | NO TRACE ID AVAILABLE")
    return None


class OpenAIAgentsExporter:
    """Exporter for Agents SDK traces and spans that forwards them to OpenTelemetry.
    
    This exporter is responsible for:
    1. Creating and configuring spans
    2. Setting span attributes based on data from the processor
    3. Managing the span lifecycle
    4. Using semantic conventions for attribute naming
    5. Interacting with the OpenTelemetry API
    6. Tracking spans to allow updating them when tasks complete
    """

    def __init__(self, tracer_provider=None):
        self.tracer_provider = tracer_provider
        # Dictionary to track active spans by their SDK span ID
        # Allows us to reference spans later during task completion
        self._active_spans = {}
        # Dictionary to track spans by trace/span ID for faster lookups
        self._span_map = {}
    
    def export_trace(self, trace: Any) -> None:
        """
        Handle exporting the trace.
        """
        tracer = get_tracer(LIBRARY_NAME, LIBRARY_VERSION, self.tracer_provider)
        trace_id = getattr(trace, 'trace_id', 'unknown')
        
        if not hasattr(trace, 'trace_id'):
            logger.warning("Cannot export trace: missing trace_id")
            return
        
        attributes = get_base_trace_attributes(trace)
        
        # Determine if this is a trace end event using status field
        # Status field is the OpenTelemetry standard way to track completion
        is_end_event = hasattr(trace, "status") and trace.status == StatusCode.OK.name
        
        # Create a unique lookup key for the trace span
        # Using trace_id for both the trace and span identifier to ensure uniqueness
        trace_lookup_key = f"span:{trace_id}:{trace_id}"
        
        # For end events, check if we already have the span
        if is_end_event and trace_lookup_key in self._span_map:
            existing_span = self._span_map[trace_lookup_key]
            
            # Check if span is already ended
            from opentelemetry.sdk.trace import Span
            span_is_ended = False
            if isinstance(existing_span, Span) and hasattr(existing_span, "_end_time"):
                span_is_ended = existing_span._end_time is not None
                
            if not span_is_ended:
                # Update with core attributes
                for key, value in attributes.items():
                    existing_span.set_attribute(key, value)
                
                # Handle error if present
                if hasattr(trace, "error") and trace.error:
                    self._handle_span_error(trace, existing_span)
                    
                # Set status to OK if no error
                else:
                    existing_span.set_status(Status(StatusCode.OK))
                
                # End the span now
                existing_span.end()
                logger.debug(f"[TRACE] Updated and ended existing trace span: {trace_id}")
                
                # Clean up our tracking resources
                self._active_spans.pop(trace_id, None)
                self._span_map.pop(trace_lookup_key, None)
                return
            else:
                logger.debug(f"Cannot update trace {trace_id} as it is already ended - creating new one")
        
        # Create the trace span
        span_name = f"{TRACE_PREFIX}.{trace.name}"
        
        # Create span directly instead of using context manager
        span = tracer.start_span(
            name=span_name,
            kind=SpanKind.INTERNAL,
            attributes=attributes
        )
        
        # Add any additional trace attributes
        if hasattr(trace, "group_id") and trace.group_id:
            span.set_attribute(CoreAttributes.GROUP_ID, trace.group_id)
            
        if hasattr(trace, "metadata") and trace.metadata:
            for key, value in trace.metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    span.set_attribute(f"trace.metadata.{key}", value)
        
        # Set the trace input as the prompt if available
        if hasattr(trace, "input") and trace.input:
            input_text = safe_serialize(trace.input)
            span.set_attribute(SpanAttributes.LLM_PROMPTS, input_text)
            span.set_attribute(WorkflowAttributes.WORKFLOW_INPUT, input_text)
            
        # Record error if present
        if hasattr(trace, "error") and trace.error:
            self._handle_span_error(trace, span)
        
        # For start events, store the span for later reference
        if not is_end_event:
            # Store the span for later updates
            self._span_map[trace_lookup_key] = span
            self._active_spans[trace_id] = {
                'span': span,
                'span_type': 'TraceSpan',
                'trace_id': trace_id,
                'parent_id': None  # Trace spans don't have parents
            }
            
            # Log the span and tracking dictionaries state for debugging
            span_context = span.get_span_context() if hasattr(span, "get_span_context") else None
            span_id_hex = f"{span_context.span_id:016x}" if span_context and hasattr(span_context, "span_id") else "unknown"
            
            logger.debug(f"[TRACE] Created and stored trace span for future reference: {trace_id}")
            logger.debug(f"[TRACE] Span context: trace_id={trace_id}, span_id={span_id_hex}")
            logger.debug(f"[TRACE] Active spans count: {len(self._active_spans)}")
            logger.debug(f"[TRACE] Span map keys: {list(self._span_map.keys())[:5]}")
        else:
            # End the span manually now that all attributes are set
            span.end()
            logger.debug(f"[TRACE] Created and immediately ended trace span: {trace_id}")
    
    def _get_parent_context(self, trace_id: str, span_id: str, parent_id: Optional[str] = None) -> Any:
        """Find the parent span context for proper span nesting.
        
        This method checks:
        1. First for an explicit parent ID in our span tracking dictionary
        2. Then checks if the trace span is the parent
        3. Falls back to the current active span context if no parent is found
        
        Args:
            trace_id: The trace ID for the current span
            span_id: The span ID for the current span
            parent_id: Optional parent span ID to look up
            
        Returns:
            The OpenTelemetry span context to use as parent
        """
        # Only attempt parent lookup if we have a parent_id
        parent_span_ctx = None
        
        if parent_id:
            # Try to find the parent span in our tracking dictionary
            parent_lookup_key = f"span:{trace_id}:{parent_id}"
            if parent_lookup_key in self._span_map:
                parent_span = self._span_map[parent_lookup_key]
                # Get the context from the parent span if it exists
                if hasattr(parent_span, "get_span_context"):
                    parent_span_ctx = parent_span.get_span_context()
                    logger.debug(f"[SPAN] Found parent span context for {parent_id}")
        
        # If parent not found by span ID, check if trace span should be the parent
        if not parent_span_ctx and parent_id is None:
            # Try using the trace span as parent
            trace_lookup_key = f"span:{trace_id}:{trace_id}"
            logger.debug(f"[SPAN] Looking for trace parent with key: {trace_lookup_key}")
            
            if trace_lookup_key in self._span_map:
                trace_span = self._span_map[trace_lookup_key]
                if hasattr(trace_span, "get_span_context"):
                    parent_span_ctx = trace_span.get_span_context()
                    logger.debug(f"[SPAN] Using trace span as parent for {span_id}")
                else:
                    logger.debug(f"[SPAN] Trace span doesn't have get_span_context method")
        
        # If we couldn't find the parent by ID, use the current span context as parent
        if not parent_span_ctx:
            # Get the current span context from the context API
            ctx = context_api.get_current()
            parent_span_ctx = trace_api.get_current_span(ctx).get_span_context()
            msg = "parent for new span" if parent_id else "parent"
            logger.debug(f"[SPAN] Using current span context as {msg}")
            
        return parent_span_ctx

    def _create_span_with_parent(self, name: str, kind: SpanKind, attributes: Dict[str, Any], 
                               parent_ctx: Any, end_immediately: bool = False) -> Any:
        """Create a span with the specified parent context.
        
        This centralizes span creation with proper parent nesting.
        
        Args:
            name: The name for the new span
            kind: The span kind (CLIENT, SERVER, etc.)
            attributes: The attributes to set on the span
            parent_ctx: The parent context to use for nesting
            end_immediately: Whether to end the span immediately
            
        Returns:
            The newly created span
        """
        # Get tracer from provider
        tracer = get_tracer(LIBRARY_NAME, LIBRARY_VERSION, self.tracer_provider)
        
        # Create span with context so we get proper nesting
        with trace_api.use_span(NonRecordingSpan(parent_ctx), end_on_exit=False):
            span = tracer.start_span(
                name=name,
                kind=kind,
                attributes=attributes
            )
        
        # Optionally end the span immediately
        if end_immediately:
            span.end()
            
        return span

    def export_span(self, span: Any) -> None:
        """Export a span to OpenTelemetry, creating or updating as needed.
        
        This method decides whether to create a new span or update an existing one
        based on whether this is a start or end event for a given span ID.
        
        For start events:
        - Create a new span and store it for later updates
        - Leave status as UNSET (in progress)
        - Do not end the span
        - Properly set parent span reference for nesting
        
        For end events:
        - Look for an existing span to update
        - If found and not ended, update with final data and end it
        - If not found or already ended, create a new complete span with all data
        - End the span with proper status
        """
        if not hasattr(span, 'span_data'):
            return
            
        span_data = span.span_data
        span_type = span_data.__class__.__name__
        span_id = getattr(span, 'span_id', 'unknown')
        trace_id = getattr(span, 'trace_id', 'unknown')
        parent_id = getattr(span, 'parent_id', None)
        
        # Check if this is a span end event
        is_end_event = hasattr(span, 'status') and span.status == StatusCode.OK.name
        
        # Unique lookup key for this span
        span_lookup_key = f"span:{trace_id}:{span_id}"
        
        # Get base attributes common to all spans
        attributes = get_base_span_attributes(span)
        
        # Get span attributes using the attribute getter
        span_attributes = get_span_attributes(span_data)
        attributes.update(span_attributes)
        
        # Log parent ID information for debugging
        if parent_id:
            logger.debug(f"[SPAN] Creating span {span_id} with parent ID: {parent_id}")
        
        # Add final output data if available for end events
        if is_end_event:
            # For agent spans, set the output
            if hasattr(span_data, 'output') and span_data.output:
                output_text = safe_serialize(span_data.output)
                # TODO this should be a semantic convention in the attributes module
                attributes[WorkflowAttributes.FINAL_OUTPUT] = output_text
                logger.debug(f"[SPAN] Added final output to attributes for span: {span_id[:8]}...")
                
            # Process token usage for generation spans
            if span_type == "GenerationSpanData":
                usage = getattr(span_data, 'usage', {})
                if usage and "token_metrics" not in attributes:
                    # Add token usage metrics to attributes
                    # TODO these should be semantic conventions in the attributes module
                    attributes["token_metrics"] = "true"
                    input_tokens = getattr(usage, "prompt_tokens", getattr(usage, "input_tokens", 0))
                    if input_tokens:
                        attributes["gen_ai.token.input.count"] = input_tokens
                    output_tokens = getattr(usage, "completion_tokens", getattr(usage, "output_tokens", 0))
                    if output_tokens:
                        attributes["gen_ai.token.output.count"] = output_tokens
                    total_tokens = getattr(usage, "total_tokens", input_tokens + output_tokens)
                    if total_tokens:
                        attributes["gen_ai.token.total.count"] = total_tokens
        
        # Log the trace ID for debugging and correlation with AgentOps API
        log_otel_trace_id(span_type)
        
        # For start events, create a new span and store it (don't end it)
        if not is_end_event:
            # Process the span based on its type
            # TODO span_name should come from the attributes module
            span_name = f"agents.{span_type.replace('SpanData', '').lower()}"
            span_kind = get_span_kind(span)
            
            # Get parent context for proper nesting
            parent_span_ctx = self._get_parent_context(trace_id, span_id, parent_id)
            
            # Create the span with proper parent context
            otel_span = self._create_span_with_parent(
                name=span_name,
                kind=span_kind,
                attributes=attributes,
                parent_ctx=parent_span_ctx
            )
            
            # Store the span for later reference
            if not isinstance(otel_span, NonRecordingSpan):
                self._span_map[span_lookup_key] = otel_span
                self._active_spans[span_id] = {
                    'span': otel_span,
                    'span_type': span_type,
                    'trace_id': trace_id,
                    'parent_id': parent_id
                }
                logger.debug(f"[SPAN] Created and stored span for future reference: {span_id}")
            
            # Handle any error information
            self._handle_span_error(span, otel_span)
            
            # DO NOT end the span for start events - we want to keep it open for updates
            return
            
        # For end events, check if we already have the span
        if span_lookup_key in self._span_map:
            existing_span = self._span_map[span_lookup_key]
            
            # Check if span is already ended
            # TODO move this import to the top of the file, unless circular import
            from opentelemetry.sdk.trace import Span
            span_is_ended = False
            if isinstance(existing_span, Span) and hasattr(existing_span, "_end_time"):
                span_is_ended = existing_span._end_time is not None
                
            if not span_is_ended:
                # Update and end the existing span
                for key, value in attributes.items():
                    existing_span.set_attribute(key, value)
                
                # Set status
                existing_span.set_status(Status(StatusCode.OK if span.status == "OK" else StatusCode.ERROR))
                
                # Handle any error information
                self._handle_span_error(span, existing_span)
                
                # End the span now
                existing_span.end()
                logger.debug(f"[SPAN] Updated and ended existing span: {span_id}")
            else:
                logger.debug(f"Cannot update span {span_id} as it is already ended - creating new one")
                # Create a new span with the complete data (already ended state)
                self.create_span(span, span_type, attributes)
        else:
            # No existing span found, create a new one with all data
            self.create_span(span, span_type, attributes)
            
        # Clean up our tracking resources
        self._active_spans.pop(span_id, None)
        self._span_map.pop(span_lookup_key, None)
    
    def create_span(self, span: Any, span_type: str, attributes: Dict[str, Any]) -> None:
        """Create a new OpenTelemetry span for complete data.
        
        This method is used for end events without a matching start event.
        It creates a complete span with all data and ends it immediately.
        
        Args:
            span: The SDK span data
            span_type: The type of span being created
            attributes: Attributes to add to the span
        """
        if not hasattr(span, 'span_data'):
            return
            
        span_data = span.span_data
        span_kind = get_span_kind(span)
        span_id = getattr(span, 'span_id', 'unknown')
        trace_id = getattr(span, 'trace_id', 'unknown')
        parent_id = getattr(span, 'parent_id', None)
        
        # Process the span based on its type
        span_name = f"agents.{span_type.replace('SpanData', '').lower()}"
        
        # Get parent context for proper nesting
        parent_span_ctx = self._get_parent_context(trace_id, span_id, parent_id)
        
        # Create span with parent context
        otel_span = self._create_span_with_parent(
            name=span_name,
            kind=span_kind,
            attributes=attributes,
            parent_ctx=parent_span_ctx
        )
        
        # Set appropriate status for end event
        otel_span.set_status(Status(StatusCode.OK if getattr(span, 'status', None) == "OK" else StatusCode.ERROR))
            
        # Record error if present
        self._handle_span_error(span, otel_span)
        
        # End the span now that all attributes are set
        otel_span.end()
        logger.debug(f"[SPAN] Created and immediately ended span: {span_id}")
        
    def _handle_span_error(self, span: Any, otel_span: Any) -> None:
        """Handle error information from spans."""
        if hasattr(span, "error") and span.error:
            # Set status to error
            status = Status(StatusCode.ERROR)
            otel_span.set_status(status)
            
            # Determine error message - handle various error formats
            error_message = "Unknown error"
            error_data = {}
            error_type = "AgentError"
            
            # Handle different error formats
            if isinstance(span.error, dict):
                error_message = span.error.get("message", span.error.get("error", "Unknown error"))
                error_data = span.error.get("data", {})
                # Extract error type if available
                if "type" in span.error:
                    error_type = span.error["type"]
                elif "code" in span.error:
                    error_type = span.error["code"]
            elif isinstance(span.error, str):
                error_message = span.error
            elif hasattr(span.error, "message"):
                error_message = span.error.message
                # Use type() for more reliable class name access
                error_type = type(span.error).__name__
            elif hasattr(span.error, "__str__"):
                # Fallback to string representation
                error_message = str(span.error)
            
            # Record the exception with proper error data
            try:
                exception = Exception(error_message)
                error_data_json = json.dumps(error_data) if error_data else "{}"
                otel_span.record_exception(
                    exception=exception,
                    attributes={"error.data": error_data_json},
                )
            except Exception as e:
                # If JSON serialization fails, use simpler approach
                logger.warning(f"Error serializing error data: {e}")
                otel_span.record_exception(Exception(error_message))
            
            # Set error attributes
            otel_span.set_attribute(CoreAttributes.ERROR_TYPE, error_type)
            otel_span.set_attribute(CoreAttributes.ERROR_MESSAGE, error_message)
    
    def cleanup(self):
        """Clean up any outstanding spans during shutdown.
        
        This ensures we don't leak span resources when the exporter is shutdown.
        """
        logger.debug(f"[EXPORTER] Cleaning up {len(self._active_spans)} active spans")
        # Clear all tracking dictionaries
        self._active_spans.clear()
        self._span_map.clear()