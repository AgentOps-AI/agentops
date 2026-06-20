"""
Standalone log() function for creating log-style spans in traces.

Provides `log(name, message, level)` to record arbitrary log entries
as spans with kind="log" for observability and debugging.
"""

from typing import Optional

from agentops.logging import logger
from agentops.sdk.core import tracer
from agentops.semconv.span_kinds import AgentOpsSpanKindValues
from agentops.semconv.span_attributes import SpanAttributes


LOG_LEVELS = {"DEFAULT", "WARNING", "ERROR"}


def log(
    name: str,
    message: str,
    level: str = "DEFAULT",
) -> None:
    """
    Create a standalone log-style span with the given name, message, and level.

    This function is designed for ad-hoc logging within traces — e.g., recording
    when a tool call limit is reached, when a decision boundary is crossed, or
    any other noteworthy point during execution.

    Args:
        name: Short identifier for the log entry (e.g. "xml_tool_call_limit_reached").
        message: Human-readable description of the log event.
        level: Severity level. One of "DEFAULT", "WARNING", or "ERROR".
               Defaults to "DEFAULT".
    """
    # Validate level
    if level not in LOG_LEVELS:
        logger.warning(f"Invalid log level '{level}'. Falling back to 'DEFAULT'.")
        level = "DEFAULT"

    if not tracer.initialized:
        logger.warning("AgentOps SDK not initialized. Cannot create log span.")
        return

    try:
        span, ctx, token = tracer.make_span(
            name,
            AgentOpsSpanKindValues.LOG.value,
            attributes={
                SpanAttributes.AGENTOPS_SPAN_KIND: AgentOpsSpanKindValues.LOG.value,
                SpanAttributes.LOG_MESSAGE: message,
                SpanAttributes.LOG_LEVEL: level,
            },
        )
        span.set_attribute(SpanAttributes.LOG_MESSAGE, message)
        span.set_attribute(SpanAttributes.LOG_LEVEL, level)
        tracer.finalize_span(span, token)
    except Exception as e:
        logger.error(f"Failed to create log span: {e}")
