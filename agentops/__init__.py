from typing import List, Optional, Union, Unpack

from agentops.config import ConfigDict

from .client import Client
from .config import Config
from .session import Session

from opentelemetry.sdk.trace import SpanProcessor
from opentelemetry.sdk.trace.export import SpanExporter
from opentelemetry.sdk.metrics.export import MetricExporter
from opentelemetry.sdk._logs.export import LogExporter
from opentelemetry.sdk.resources import SERVICE_NAME
from opentelemetry.propagators.textmap import TextMapPropagator
from opentelemetry.util.re import parse_env_headers

from typing import Dict

# Client global instance; one per process runtime
_client = Client()

def init(
    api_key: Optional[str] = None,
    parent_key: Optional[str] = None,
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
    exporter: Optional[SpanExporter] = None,
    processor: Optional[SpanProcessor] = None,
) -> Union[Session, None]:
    """
    Initializes the AgentOps singleton pattern.

    Args:
        api_key (str, optional): API Key for AgentOps services. If none is provided, key will
            be read from the AGENTOPS_API_KEY environment variable.
        parent_key (str, optional): Organization key to give visibility of all user sessions the user's organization. If none is provided, key will
            be read from the AGENTOPS_PARENT_KEY environment variable.
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
        exporter (SpanExporter): Custom span exporter for OpenTelemetry trace data. If provided,
            will be used instead of the default OTLPSpanExporter. Not needed if processor is specified.
        processor (SpanProcessor): Custom span processor for OpenTelemetry trace data. If provided,
            takes precedence over exporter. Used for complete control over span processing.
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
        parent_key=parent_key,
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
        exporter=exporter,
        processor=processor,
    )


def configure(**kwargs: Unpack[ConfigDict]):
    """Update client configuration"""
    _client.configure(**kwargs)


def start_session(**kwargs) -> Optional[Session]:
    """Start a new session for recording events.

    Args:
        tags (List[str], optional): Tags that can be used for grouping or sorting later.
            e.g. ["test_run"]

    Returns:
        Optional[Session]: Returns Session if successful, None otherwise.
    """
    return _client.start_session(**kwargs)


def end_session(
    end_state: str,
    end_state_reason: Optional[str] = None,
    video: Optional[str] = None,
    is_auto_end: Optional[bool] = False,
):
    """
    End the current session with the AgentOps service.

    Args:
        end_state (str): The final state of the session. Options: Success, Fail, or Indeterminate.
        end_state_reason (str, optional): The reason for ending the session.
        video (str, optional): URL to a video recording of the session
    """
    _client.end_session(end_state, end_state_reason, video, is_auto_end)


def record():
    """
    Record an event with the AgentOps service.

    Args:
        event (Event): The event to record.
    """
    raise NotImplementedError


def add_tags(tags: List[str]):
    """
    Append to session tags at runtime.

    TODO: How do we retrieve the session context to add tags to?

    Args:
        tags (List[str]): The list of tags to append.
    """
    _client.add_tags(tags)


def set_tags(tags: List[str]):
    """
    Replace session tags at runtime.

    Args:
        tags (List[str]): The list of tags to set.
    """
    _client.set_tags(tags)


# Mostly used for unit testing -
# prevents unexpected sessions on new tests
def end_all_sessions() -> None:
    """End all active sessions"""
    _client.end_all_sessions()


# For backwards compatibility and testing
def get_client() -> Client:
    """Get the singleton client instance"""
    return _client
