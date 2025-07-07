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


def fetch_trace_stats(trace_id: str) -> Optional[dict]:
    """
    Fetch statistics for a trace from the AgentOps public API.

    Args:
        trace_id: The trace ID to fetch stats for.

    Returns:
        Dictionary containing trace statistics, or None if fetching fails.
    """
    try:
        # Import here to avoid circular imports
        from agentops import get_client
        from agentops.client.http.http_client import HttpClient
        
        client = get_client()
        
        # Check if client is initialized and has auth token
        if not client.initialized or not hasattr(client.api, 'v4') or not hasattr(client.api.v4, 'auth_token'):
            logger.debug("Client not properly initialized for fetching trace stats")
            return None
            
        # Get the API endpoint and auth token
        endpoint = client.config.endpoint
        auth_token = client.api.v4.auth_token
        
        # Construct the stats URL
        stats_url = f"{endpoint}/public/v1/traces/{trace_id}/stats"
        
        # Make the API request
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        response = HttpClient.request("GET", stats_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.debug(f"Failed to fetch trace stats: {response.status_code}")
            return None
            
    except Exception as e:
        logger.debug(f"Error fetching trace stats: {e}")
        return None


def log_trace_url(span: Union[Span, ReadableSpan], title: Optional[str] = None) -> None:
    """
    Log the trace URL for the AgentOps dashboard along with session statistics.

    Args:
        span: The span to log the URL for.
        title: Optional title for the session.
    """
    session_url = get_trace_url(span)
    
    # Get trace ID for stats
    trace_id = span.context.trace_id
    if isinstance(trace_id, int):
        trace_id = format(trace_id, "032x")
    
    # Log the session URL
    logger.info(colored(f"\x1b[34mSession Replay for {title} trace: {session_url}\x1b[0m", "blue"))
    
    # Fetch and log session statistics
    stats = fetch_trace_stats(trace_id)
    if stats:
        try:
            # Extract the metrics the user requested
            span_count = stats.get('span_count', 0)
            llm_calls = stats.get('llm_calls', 0)
            tool_calls = stats.get('tool_calls', 0)
            total_cost = stats.get('total_cost', '0.0000')
            
            # Format the statistics message
            stats_message = (
                f"📊 Session Stats: {span_count} spans, "
                f"{tool_calls} tools, {llm_calls} LLM calls, "
                f"${total_cost} total cost"
            )
            
            logger.info(colored(f"\x1b[32m{stats_message}\x1b[0m", "green"))
            
        except Exception as e:
            logger.debug(f"Error parsing trace stats: {e}")
    else:
        logger.debug("Could not fetch session statistics")
