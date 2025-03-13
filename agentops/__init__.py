from typing import Dict, List, Optional, Union, Any

from .client import Client
from .sdk.commands import record as sdk_record, start_span as sdk_start_span, end_span as sdk_end_span
from .semconv.span_kinds import SpanKind
import agentops.legacy as legacy

# Client global instance; one per process runtime
_client = Client()


def init(
    api_key: Optional[str] = None,
    endpoint: Optional[str] = None,
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
    # List of valid parameters that can be passed to configure
    valid_params = {
        "api_key",
        "endpoint",
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


def start_session(**kwargs):
    """Start a new session for recording events.

    Args:
        tags (List[str], optional): Tags that can be used for grouping or sorting later.
            e.g. ["test_run"]

    Returns:
        Optional[Session]: Returns Session if successful, None otherwise.
    """
    return _client.start_session(**kwargs)


def end_session(span, token):
    """
    End a previously started AgentOps session.

    This function ends the session span and detaches the context token,
    completing the session lifecycle.

    Args:
        span: The span returned by start_session
        token: The token returned by start_session
    """
    legacy.end_session(span, token)


def start_span(
    name: str = "manual_span",
    span_kind: str = SpanKind.OPERATION,
    attributes: Optional[Dict[str, Any]] = None,
    version: Optional[int] = None,
):
    """
    Start a new span manually.

    This function creates and starts a new span, which can be used to track
    operations. The span will remain active until end_span is called with
    the returned span and token.

    Args:
        name: Name of the span
        span_kind: Kind of span (defaults to SpanKind.OPERATION)
        attributes: Optional attributes to set on the span
        version: Optional version identifier for the span

    Returns:
        A tuple of (span, token) that should be passed to end_span
    """
    return sdk_start_span(name, span_kind, attributes, version)


def end_span(span, token):
    """
    End a previously started span.

    This function ends the span and detaches the context token,
    completing the span lifecycle.

    Args:
        span: The span returned by start_span
        token: The token returned by start_span
    """
    sdk_end_span(span, token)


def record(message: str, attributes: Optional[Dict[str, Any]] = None):
    """
    Record an event with a message within the current session.

    This function creates a simple operation span with the provided message
    and attributes, which will be automatically associated with the current session.

    Args:
        message: The message to record
        attributes: Optional attributes to set on the span
    """
    sdk_record(message, attributes)


def add_tags(tags: List[str]):
    """
    Append to session tags at runtime.

    TODO: How do we retrieve the session context to add tags to?

    Args:
        tags (List[str]): The list of tags to append.
    """
    raise NotImplementedError


def set_tags(tags: List[str]):
    """
    Replace session tags at runtime.

    Args:
        tags (List[str]): The list of tags to set.
    """
    raise NotImplementedError


# For backwards compatibility and testing
def get_client() -> Client:
    """Get the singleton client instance"""
    return _client
