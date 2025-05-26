"""OpenAI Agents SDK Instrumentation Exporter for AgentOps

This module handles the conversion of Agents SDK spans to OpenTelemetry spans.
It manages the complete span lifecycle, attribute application, and proper span hierarchy.

See the README.md in this directory for complete documentation on:
- Span lifecycle management approach
- Serialization rules for attributes
- Structured attribute handling
- Semantic conventions usage

IMPORTANT FOR TESTING:
- Tests should verify attribute existence using MessageAttributes constants
- Do not check for the presence of SpanAttributes.LLM_COMPLETIONS
- Verify individual content/tool attributes instead of root attributes
"""

import json
from typing import Any, Dict, Optional

from opentelemetry import trace, context as context_api
from opentelemetry.trace import get_tracer, SpanKind, Status, StatusCode, NonRecordingSpan
from opentelemetry import trace as trace_api
from opentelemetry.sdk.trace import Span

from agentops.logging import logger
from agentops.semconv import (
    CoreAttributes,
)

from agentops.instrumentation.common.attributes import (
    get_base_trace_attributes,
    get_base_span_attributes,
)

from agentops.instrumentation.openai_agents import LIBRARY_NAME, LIBRARY_VERSION
from agentops.instrumentation.openai_agents.attributes.common import (
    get_span_attributes,
)
# Removed: from agentops.helpers import safe_serialize
# full_prompt_contextvar will be imported and used by attributes.common, not directly here.


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


def get_span_kind(span: Any) -> SpanKind:
    """Determine the appropriate span kind based on span type."""
    span_data = span.span_data
    span_type = span_data.__class__.__name__

    if span_type == "AgentSpanData":
        return SpanKind.CONSUMER
    elif span_type in ["FunctionSpanData", "GenerationSpanData", "ResponseSpanData"]:
        return SpanKind.CLIENT
    else:
        return SpanKind.INTERNAL


def get_span_name(span: Any) -> str:
    """Get the name of the span based on its type and attributes."""
    span_data = span.span_data
    span_type = span_data.__class__.__name__

    if hasattr(span_data, "name") and span_data.name:
        return span_data.name
    else:
        return span_type.replace("SpanData", "").lower()  # fallback


def _get_span_lookup_key(trace_id: str, span_id: str) -> str:
    """Generate a unique lookup key for spans based on trace and span IDs.

    This key is used to track spans in the exporter and allows for efficient
    lookups and management of spans during their lifecycle.

    Args:
        trace_id: The trace ID for the current span
        span_id: The span ID for the current span

    Returns:
        str: A unique lookup key for the span
    """
    return f"span:{trace_id}:{span_id}"


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
        trace_id = getattr(trace, "trace_id", "unknown")

        if not hasattr(trace, "trace_id"):
            logger.debug("Cannot export trace: missing trace_id")
            return

        # Determine if this is a trace end event using status field
        # We use the status field to determine if this is an end event
        is_end_event = hasattr(trace, "status") and trace.status == StatusCode.OK.name
        trace_lookup_key = _get_span_lookup_key(trace_id, trace_id)
        attributes = get_base_trace_attributes(trace)

        # For end events, check if we already have the span
        if is_end_event and trace_lookup_key in self._span_map:
            existing_span = self._span_map[trace_lookup_key]

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

                existing_span.end()

                # Clean up our tracking resources
                self._active_spans.pop(trace_id, None)
                self._span_map.pop(trace_lookup_key, None)
                return

        # Create span directly instead of using context manager
        span = tracer.start_span(name=trace.name, kind=SpanKind.INTERNAL, attributes=attributes)

        # Add any additional trace attributes
        if hasattr(trace, "group_id") and trace.group_id:
            span.set_attribute(CoreAttributes.GROUP_ID, trace.group_id)

        if hasattr(trace, "metadata") and trace.metadata:
            for key, value in trace.metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    span.set_attribute(f"trace.metadata.{key}", value)

        # Record error if present
        if hasattr(trace, "error") and trace.error:
            self._handle_span_error(trace, span)

        # For start events, store the span for later reference
        if not is_end_event:
            self._span_map[trace_lookup_key] = span
            self._active_spans[trace_id] = {
                "span": span,
                "span_type": "TraceSpan",
                "trace_id": trace_id,
                "parent_id": None,  # Trace spans don't have parents
            }
        else:
            span.end()

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
        parent_span_ctx = None

        if parent_id:
            # Try to find the parent span in our tracking dictionary
            parent_lookup_key = f"span:{trace_id}:{parent_id}"
            if parent_lookup_key in self._span_map:
                parent_span = self._span_map[parent_lookup_key]
                # Get the context from the parent span if it exists
                if hasattr(parent_span, "get_span_context"):
                    parent_span_ctx = parent_span.get_span_context()

        # If parent not found by span ID, check if trace span should be the parent
        if not parent_span_ctx and parent_id is None:
            # Try using the trace span as parent
            trace_lookup_key = _get_span_lookup_key(trace_id, trace_id)

            if trace_lookup_key in self._span_map:
                trace_span = self._span_map[trace_lookup_key]
                if hasattr(trace_span, "get_span_context"):
                    parent_span_ctx = trace_span.get_span_context()

        # If we couldn't find the parent by ID, use the current span context as parent
        if not parent_span_ctx:
            # Get the current span context from the context API
            ctx = context_api.get_current()
            parent_span_ctx = trace_api.get_current_span(ctx).get_span_context()

        return parent_span_ctx

    def _create_span_with_parent(
        self, name: str, kind: SpanKind, attributes: Dict[str, Any], parent_ctx: Any, end_immediately: bool = False
    ) -> Any:
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
            span = tracer.start_span(name=name, kind=kind, attributes=attributes)

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
        if not hasattr(span, "span_data"):
            return

        span_data = span.span_data
        span_type = span_data.__class__.__name__
        span_id = getattr(span, "span_id", "unknown")
        trace_id = getattr(span, "trace_id", "unknown")
        parent_id = getattr(span, "parent_id", None)

        # logger.debug(f"[Exporter] export_span called for SDK span_id: {span_id}, name: {getattr(span_data, 'name', span_type)}, type: {span_type}, trace_id: {trace_id}, parent_id: {parent_id}")

        # Check if this is a span end event
        is_end_event = hasattr(span, "status") and span.status == StatusCode.OK.name

        # Unique lookup key for this span
        span_lookup_key = _get_span_lookup_key(trace_id, span_id)

        # span_data augmentation with _full_prompt_from_wrapper_context is removed.
        # attributes/common.py will now directly get the contextvar.

        # Log content of span_data.response before getting attributes
        # if hasattr(span_data, 'response') and span_data.response is not None:
        # logger.debug(f"[Exporter] SDK span_id: {span_id} - span_data.response before get_span_attributes: {safe_serialize(vars(span_data.response)) if hasattr(span_data.response, '__dict__') else safe_serialize(span_data.response)}")
        # elif span_type in ["ResponseSpanData", "GenerationSpanData"]: # Only log absence for relevant types
        # logger.debug(f"[Exporter] SDK span_id: {span_id} - span_data.response is None or not present before get_span_attributes for {span_type}.")

        attributes = get_base_span_attributes(span)  # Basic attributes from the SDK span object
        span_specific_attributes = get_span_attributes(span_data)  # Type-specific attributes from SpanData
        attributes.update(span_specific_attributes)

        # logger.debug(f"[Exporter] SDK span_id: {span_id} - Combined attributes before OTel span creation/update: {safe_serialize(attributes)}")

        if is_end_event:
            # For end events, ensure all attributes from span_data are captured
            # get_span_attributes should ideally get everything needed based on the final state of span_data
            pass  # Attributes are already updated above

        # Log the trace ID for debugging and correlation with AgentOps API
        log_otel_trace_id(span_type)

        # For start events, create a new span and store it (don't end it)
        if not is_end_event:
            span_name = get_span_name(span)  # Get OTel span name
            span_kind = get_span_kind(span)  # Get OTel span kind

            parent_span_ctx = self._get_parent_context(trace_id, span_id, parent_id)

            otel_span = self._create_span_with_parent(
                name=span_name, kind=span_kind, attributes=attributes, parent_ctx=parent_span_ctx
            )
            # logger.debug(f"[Exporter] SDK span_id: {span_id} (START event) - CREATED OTel span with OTel_span_id: {otel_span.context.span_id if otel_span else 'None'}")

            if not isinstance(otel_span, NonRecordingSpan):
                self._span_map[span_lookup_key] = otel_span
                self._active_spans[span_id] = {  # Use SDK span_id as key for _active_spans
                    "span": otel_span,
                    "span_type": span_type,
                    "trace_id": trace_id,  # SDK trace_id
                    "parent_id": parent_id,  # SDK parent_id
                }
                # logger.debug(f"[Exporter] SDK span_id: {span_id} (START event) - Stored OTel span in _span_map and _active_spans.")

            self._handle_span_error(span, otel_span)  # Handle error for start event too
            return

        # For end events, check if we already have the span
        if span_lookup_key in self._span_map:
            existing_span = self._span_map[span_lookup_key]
            # logger.debug(f"[Exporter] SDK span_id: {span_id} (END event) - Found existing OTel span in _span_map with OTel_span_id: {existing_span.context.span_id}")

            span_is_ended = False
            if isinstance(existing_span, Span) and hasattr(existing_span, "_end_time"):
                span_is_ended = existing_span._end_time is not None
            # logger.debug(f"[Exporter] SDK span_id: {span_id} (END event) - Existing OTel span was_ended: {span_is_ended}")

            if not span_is_ended:
                for key, value in attributes.items():  # Update with final attributes
                    existing_span.set_attribute(key, value)
                # logger.debug(f"[Exporter] SDK span_id: {span_id} (END event) - Updated attributes on existing OTel span.")

                existing_span.set_status(
                    Status(StatusCode.OK if getattr(span, "status", "OK") == "OK" else StatusCode.ERROR)
                )
                self._handle_span_error(span, existing_span)
                existing_span.end()
                # logger.debug(f"[Exporter] SDK span_id: {span_id} (END event) - ENDED existing OTel span.")
            else:  # Span already ended, create a new one (should be rare if logic is correct)
                logger.warning(
                    f"[Exporter] SDK span_id: {span_id} (END event) - Attempting to end an ALREADY ENDED OTel span: {span_lookup_key}. Creating a new one instead."
                )
                self.create_span(span, span_type, attributes, is_already_ended=True)
        else:  # No existing span found for end event, create a new one
            logger.warning(
                f"[Exporter] SDK span_id: {span_id} (END event) - No active OTel span found for end event: {span_lookup_key}. Creating a new one."
            )
            self.create_span(span, span_type, attributes, is_already_ended=True)

        self._active_spans.pop(span_id, None)
        self._span_map.pop(span_lookup_key, None)
        # logger.debug(f"[Exporter] SDK span_id: {span_id} (END event) - Popped from _active_spans and _span_map.")

    def create_span(
        self, span: Any, span_type: str, attributes: Dict[str, Any], is_already_ended: bool = False
    ) -> None:
        """Create a new span with the provided data and end it immediately.

        This method creates a span using the appropriate parent context, applies
        all attributes, and ends it immediately since it's for spans that are
        already in an ended state.

        Args:
            span: The span data from the Agents SDK
            span_type: The type of span being created
            attributes: The attributes to set on the span
        """
        # For simplicity and backward compatibility, use None as the parent context
        # In a real implementation, you might want to look up the parent
        parent_ctx = None
        if hasattr(span, "parent_id") and span.parent_id:
            # Get parent context from trace_id and parent_id if available
            parent_ctx = self._get_parent_context(
                getattr(span, "trace_id", "unknown"), getattr(span, "id", "unknown"), span.parent_id
            )

        name = get_span_name(span)
        kind = get_span_kind(span)

        # Create the span with parent context and end it immediately
        self._create_span_with_parent(
            name=name, kind=kind, attributes=attributes, parent_ctx=parent_ctx, end_immediately=True
        )

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
        # Clear all tracking dictionaries
        self._active_spans.clear()
        self._span_map.clear()
