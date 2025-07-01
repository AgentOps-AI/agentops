"""
Helpers for interacting with the AgentOps dashboard.
"""

from typing import Union, Optional
from termcolor import colored
from opentelemetry.sdk.trace import Span, ReadableSpan
from agentops.logging import logger


def get_trace_url(span: Union[Span, ReadableSpan]) -> str:
    """
    Generate a trace URL for a direct link to the session on the AgentOps dashboard.

    Args:
        span: The span to generate the URL for.

    Returns:
        The session URL.
    """
    trace_id: Union[int, str] = span.context.trace_id

    # Convert trace_id to hex string if it's not already
    # We don't add dashes to this to format it as a UUID since the dashboard doesn't either
    if isinstance(trace_id, int):
        trace_id = format(trace_id, "032x")

    # Get the app_url from the config - import here to avoid circular imports
    from agentops import get_client

    app_url = get_client().config.app_url

    return f"{app_url}/sessions?trace_id={trace_id}"


def log_trace_url(span: Union[Span, ReadableSpan], title: Optional[str] = None) -> None:
    """
    Log the trace URL for the AgentOps dashboard.

    Args:
        span: The span to log the URL for.
    """
    session_url = get_trace_url(span)

    # Provide a sensible default if no title is supplied to ensure readable
    # log output.  Using `colored` alone is sufficient to add ANSI colour codes
    # – pre-pending our own escape sequences resulted in duplicated formatting
    # and garbled terminal output.
    pretty_title = f"{title} " if title else ""
    logger.info(colored(f"Session Replay for {pretty_title}trace: {session_url}", "blue"))
