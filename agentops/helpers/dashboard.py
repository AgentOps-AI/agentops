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

    # Determine if this is the first time we're logging a session URL.
    # We keep module-level state to avoid repeating the library list on subsequent calls.
    global _has_logged_first_session_url  # type: ignore  # Runtime attribute assignment below

    # Fallback in case the attribute doesn't exist yet
    if "_has_logged_first_session_url" not in globals():
        _has_logged_first_session_url = False  # type: ignore

    libraries_text = ""
    if not _has_logged_first_session_url:
        try:
            # Import lazily to avoid circular dependencies if instrumentation isn't enabled.
            from agentops.instrumentation import get_active_libraries

            active_libs = sorted(get_active_libraries())
            if active_libs:
                libraries_text = f" | Instrumented libraries: {', '.join(active_libs)}"
        except Exception:
            # Silently ignore any errors while attempting to fetch instrumentation data.
            pass

        _has_logged_first_session_url = True  # type: ignore

    logger.info(colored(f"\x1b[34mSession Replay for {title} trace: {session_url}{libraries_text}\x1b[0m", "blue"))
