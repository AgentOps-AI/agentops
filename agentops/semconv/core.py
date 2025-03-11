"""Core attributes applicable to all spans."""


class CoreAttributes:
    """Core attributes applicable to all spans."""

    # Status attributes
    ERROR_TYPE = "error.type"          # Type of error if status is error
    ERROR_MESSAGE = "error.message"    # Error message if status is error

    IN_FLIGHT = "agentops.in-flight"   # Whether the span is in-flight
    EXPORT_IMMEDIATELY = "agentops.export.immediate"  # Whether the span should be exported immediately
