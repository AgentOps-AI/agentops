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
    logger.info(colored(f"\x1b[34mSession Replay for {title} trace: {session_url}\x1b[0m", "blue"))
    
    # Get trace statistics if available
    try:
        from agentops.sdk.core import tracer
        
        if tracer.initialized and tracer._internal_processor:
            trace_id = span.context.trace_id
            stats = tracer.get_trace_statistics(trace_id)
            
            # Only print statistics if we have collected some data
            if stats["total_spans"] > 0:
                logger.info(colored("\x1b[34m📊 Session Statistics:\x1b[0m", "blue"))
                logger.info(colored(f"\x1b[34m  • Total Spans: {stats['total_spans']}\x1b[0m", "blue"))
                logger.info(colored(f"\x1b[34m  • Tools: {stats['tool_count']}\x1b[0m", "blue"))
                logger.info(colored(f"\x1b[34m  • LLM Calls: {stats['llm_count']}\x1b[0m", "blue"))
                logger.info(colored(f"\x1b[34m  • Total Cost: ${stats['total_cost']:.4f}\x1b[0m", "blue"))
    except Exception as e:
        # Silently ignore errors in statistics collection to not break the main flow
        logger.debug(f"Failed to get trace statistics: {e}")
