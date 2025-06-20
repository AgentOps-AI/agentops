"""Core attributes applicable to all spans."""


class CoreAttributes:
    """Core attributes applicable to all spans."""

    # Error attributes
    ERROR_TYPE = "error.type"  # Type of error if status is error
    ERROR_MESSAGE = "error.message"  # Error message if status is error

    TAGS = "agentops.tags"  # Tags passed to agentops.init

    # Trace context attributes
    TRACE_ID = "trace.id"  # Trace ID
    SPAN_ID = "span.id"  # Span ID
    PARENT_ID = "parent.id"  # Parent ID
    GROUP_ID = "group.id"  # Group ID

    # Note: WORKFLOW_NAME is defined in WorkflowAttributes to avoid duplication
