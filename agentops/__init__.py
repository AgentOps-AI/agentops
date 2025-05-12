# For backwards compatibility
from agentops.legacy import (
    start_session,
    end_session,
    track_agent,
    track_tool,
    end_all_sessions,
    Session,
    ToolEvent,
    ErrorEvent,
    ActionEvent,
    LLMEvent,
)  # type: ignore

from typing import List, Optional, Union
from agentops.client import Client


# Client global instance; one per process runtime
_client = Client()


def get_client() -> Client:
    """Get the singleton client instance"""
    global _client

    return _client


def record(event):
    """
    Legacy function to record an event. This is kept for backward compatibility.

    In the current version, this simply sets the end_timestamp on the event.

    Args:
        event: The event to record
    """
    from agentops.helpers.time import get_ISO_time

    # TODO: Manual timestamp assignment is a temporary fix; should use proper event lifecycle
    if event and hasattr(event, "end_timestamp"):
        event.end_timestamp = get_ISO_time()

    return event


def init(
    api_key: Optional[str] = None,
    endpoint: Optional[str] = None,
    app_url: Optional[str] = None,
    max_wait_time: Optional[int] = None,
    max_queue_size: Optional[int] = None,
    tags: Optional[List[str]] = None,
    default_tags: Optional[List[str]] = None,
    instrument_llm_calls: Optional[bool] = None,
    auto_start_session: Optional[bool] = None,
    auto_init: Optional[bool] = None,
    skip_auto_end_session: Optional[bool] = None,
    env_data_opt_out: Optional[bool] = None,
    log_level: Optional[Union[str, int]] = None,
    fail_safe: Optional[bool] = None,
    exporter_endpoint: Optional[str] = None,
    **kwargs,
):
    """
    Initializes the AgentOps SDK.

    Args:
        api_key (str, optional): API Key for AgentOps services. If none is provided, key will
            be read from the AGENTOPS_API_KEY environment variable.
        endpoint (str, optional): The endpoint for the AgentOps service. If none is provided, key will
            be read from the AGENTOPS_API_ENDPOINT environment variable. Defaults to 'https://api.agentops.ai'.
        app_url (str, optional): The dashboard URL for the AgentOps app. If none is provided, key will
            be read from the AGENTOPS_APP_URL environment variable. Defaults to 'https://app.agentops.ai'.
        max_wait_time (int, optional): The maximum time to wait in milliseconds before flushing the queue.
            Defaults to 5,000 (5 seconds)
        max_queue_size (int, optional): The maximum size of the event queue. Defaults to 512.
        tags (List[str], optional): [Deprecated] Use `default_tags` instead.
        default_tags (List[str], optional): Default tags for the sessions that can be used for grouping or sorting later (e.g. ["GPT-4"]).
        instrument_llm_calls (bool): Whether to instrument LLM calls and emit LLMEvents.
        auto_start_session (bool): Whether to start a session automatically when the client is created.
        auto_init (bool): Whether to automatically initialize the client on import. Defaults to True.
        skip_auto_end_session (optional, bool): Don't automatically end session based on your framework's decision-making
            (i.e. Crew determining when tasks are complete and ending the session)
        env_data_opt_out (bool): Whether to opt out of collecting environment data.
        log_level (str, int): The log level to use for the client. Defaults to 'CRITICAL'.
        fail_safe (bool): Whether to suppress errors and continue execution when possible.
        exporter_endpoint (str, optional): Endpoint for the exporter. If none is provided, key will
            be read from the AGENTOPS_EXPORTER_ENDPOINT environment variable.
        **kwargs: Additional configuration parameters to be passed to the client.
    """
    global _client

    # Merge tags and default_tags if both are provided
    merged_tags = None
    if tags and default_tags:
        merged_tags = list(set(tags + default_tags))
    elif tags:
        merged_tags = tags
    elif default_tags:
        merged_tags = default_tags

    return _client.init(
        api_key=api_key,
        endpoint=endpoint,
        app_url=app_url,
        max_wait_time=max_wait_time,
        max_queue_size=max_queue_size,
        default_tags=merged_tags,
        instrument_llm_calls=instrument_llm_calls,
        auto_start_session=auto_start_session,
        auto_init=auto_init,
        skip_auto_end_session=skip_auto_end_session,
        env_data_opt_out=env_data_opt_out,
        log_level=log_level,
        fail_safe=fail_safe,
        exporter_endpoint=exporter_endpoint,
        **kwargs,
    )


def configure(**kwargs):
    """Update client configuration

    Args:
        **kwargs: Configuration parameters. Supported parameters include:
            - api_key: API Key for AgentOps services
            - endpoint: The endpoint for the AgentOps service
            - app_url: The dashboard URL for the AgentOps app
            - max_wait_time: Maximum time to wait in milliseconds before flushing the queue
            - max_queue_size: Maximum size of the event queue
            - default_tags: Default tags for the sessions
            - instrument_llm_calls: Whether to instrument LLM calls
            - auto_start_session: Whether to start a session automatically
            - skip_auto_end_session: Don't automatically end session
            - env_data_opt_out: Whether to opt out of collecting environment data
            - log_level: The log level to use for the client
            - fail_safe: Whether to suppress errors and continue execution
            - exporter: Custom span exporter for OpenTelemetry trace data
            - processor: Custom span processor for OpenTelemetry trace data
            - exporter_endpoint: Endpoint for the exporter
    """
    global _client

    # List of valid parameters that can be passed to configure
    valid_params = {
        "api_key",
        "endpoint",
        "app_url",
        "max_wait_time",
        "max_queue_size",
        "default_tags",
        "instrument_llm_calls",
        "auto_start_session",
        "skip_auto_end_session",
        "env_data_opt_out",
        "log_level",
        "fail_safe",
        "exporter",
        "processor",
        "exporter_endpoint",
    }

    # Check for invalid parameters
    invalid_params = set(kwargs.keys()) - valid_params
    if invalid_params:
        from .logging.config import logger

        logger.warning(f"Invalid configuration parameters: {invalid_params}")

    _client.configure(**kwargs)


__all__ = [
    "init",
    "configure",
    "get_client",
    "record",
    "start_session",
    "end_session",
    "track_agent",
    "track_tool",
    "end_all_sessions",
    "Session",
    "ToolEvent",
    "ErrorEvent",
    "ActionEvent",
    "LLMEvent",
]
