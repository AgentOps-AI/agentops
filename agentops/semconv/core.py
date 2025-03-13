"""Core attributes applicable to all spans."""


class CoreAttributes:
    """Core attributes applicable to all spans."""

    # Error attributes
    ERROR_TYPE = "error.type"  # Type of error if status is error
    ERROR_MESSAGE = "error.message"  # Error message if status is error

    IN_FLIGHT = "agentops.in-flight"  # Whether the span is in-flight
    EXPORT_IMMEDIATELY = "agentops.export.immediate"  # Whether the span should be exported immediately

    # Trace context attributes
    TRACE_ID = "trace.id"  # Trace ID
    SPAN_ID = "span.id"  # Span ID
    PARENT_ID = "parent.id"  # Parent ID
    PARENT_SPAN_ID = "parent.span.id"  # Parent span ID
    PARENT_TRACE_ID = "parent.trace.id"  # Parent trace ID
    PARENT_SPAN_KIND = "parent.span.kind"  # Parent span kind
    PARENT_SPAN_NAME = "parent.span.name"  # Parent span name
    GROUP_ID = "group.id"  # Group ID

    # Note: WORKFLOW_NAME is defined in WorkflowAttributes to avoid duplication
