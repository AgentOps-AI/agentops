"""Core attributes applicable to all spans."""

class CoreAttributes:
    """Core attributes applicable to all spans."""
    
    # Status attributes
    ERROR_TYPE = "error.type"          # Type of error if status is error
    ERROR_MESSAGE = "error.message"    # Error message if status is error

    WORKFLOW_NAME = "workflow.name"    # Name of the workflow
    TRACE_ID = "trace.id"              # Trace ID
    SPAN_ID = "span.id"                # Span ID
    PARENT_SPAN_ID = "parent.span.id"  # Parent span ID
    PARENT_TRACE_ID = "parent.trace.id" # Parent trace ID
    PARENT_SPAN_KIND = "parent.span.kind" # Parent span kind
    PARENT_SPAN_NAME = "parent.span.name" # Parent span name
    PARENT_ID = "parent.id" # Parent ID
    
