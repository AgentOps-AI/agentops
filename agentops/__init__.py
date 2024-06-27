# agentops/__init__.py
import functools
import os
import logging
from typing import Optional, List, Union
from .client import Client
from .config import Configuration
from .event import Event, ActionEvent, LLMEvent, ToolEvent, ErrorEvent
from .decorators import record_function
from .agent import track_agent
from .log_config import logger

try:
    from .partners.langchain_callback_handler import (
        LangchainCallbackHandler,
        AsyncLangchainCallbackHandler,
    )
except ModuleNotFoundError:
    pass

is_initialized = False


def noop(*args, **kwargs):
    return


def check_init(child_function):
    @functools.wraps(child_function)
    def wrapper(*args, **kwargs):
        if is_initialized:
            return child_function(*args, **kwargs)
        else:
            return noop(*args, **kwargs)

    return wrapper


def init(
    api_key: Optional[str] = None,
    parent_key: Optional[str] = None,
    endpoint: Optional[str] = None,
    max_wait_time: Optional[int] = None,
    max_queue_size: Optional[int] = None,
    tags: Optional[List[str]] = None,
    override: Optional[bool] = None,  # Deprecated
    instrument_llm_calls=True,
    auto_start_session=True,
    inherited_session_id: Optional[str] = None,
    skip_auto_end_session: Optional[bool] = False,
):
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
            Defaults to 30,000 (30 seconds)
        max_queue_size (int, optional): The maximum size of the event queue. Defaults to 100.
        tags (List[str], optional): Tags for the sessions that can be used for grouping or
            sorting later (e.g. ["GPT-4"]).
        override (bool, optional): [Deprecated] Use `instrument_llm_calls` instead. Whether to instrument LLM calls and emit LLMEvents..
        instrument_llm_calls (bool): Whether to instrument LLM calls and emit LLMEvents..
        auto_start_session (bool): Whether to start a session automatically when the client is created.
        inherited_session_id (optional, str): Init Agentops with an existing Session
        skip_auto_end_session (optional, bool): Don't automatically end session based on your framework's decision making
    Attributes:
    """
    logging_level = os.getenv("AGENTOPS_LOGGING_LEVEL")
    log_levels = {
        "CRITICAL": logging.CRITICAL,
        "ERROR": logging.ERROR,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "DEBUG": logging.DEBUG,
    }
    logger.setLevel(log_levels.get(logging_level or "INFO", "INFO"))

    c = Client(
        api_key=api_key,
        parent_key=parent_key,
        endpoint=endpoint,
        max_wait_time=max_wait_time,
        max_queue_size=max_queue_size,
        tags=tags,
        override=override,
        instrument_llm_calls=instrument_llm_calls,
        auto_start_session=auto_start_session,
        inherited_session_id=inherited_session_id,
        skip_auto_end_session=skip_auto_end_session,
    )

    global is_initialized
    is_initialized = True

    return inherited_session_id or c.current_session_id


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
        is_auto_end (bool, optional): is this an automatic use of end_session and should be skipped with bypass_auto_end_session
    """
    Client().end_session(
        end_state=end_state,
        end_state_reason=end_state_reason,
        video=video,
        is_auto_end=is_auto_end,
    )


def start_session(
    tags: Optional[List[str]] = None,
    config: Optional[Configuration] = None,
    inherited_session_id: Optional[str] = None,
):
    """
    Start a new session for recording events.

    Args:
        tags (List[str], optional): Tags that can be used for grouping or sorting later.
            e.g. ["test_run"].
        config: (Configuration, optional): Client configuration object
    """

    try:
        sess_result = Client().start_session(tags, config, inherited_session_id)

        global is_initialized
        is_initialized = True

        return sess_result
    except Exception:
        pass


@check_init
def record(event: Union[Event, ErrorEvent]):
    """
    Record an event with the AgentOps service.

    Args:
        event (Event): The event to record.
    """
    Client().record(event)


@check_init
def add_tags(tags: List[str]):
    """
    Append to session tags at runtime.

    Args:
        tags (List[str]): The list of tags to append.
    """
    Client().add_tags(tags)


@check_init
def set_tags(tags: List[str]):
    """
    Replace session tags at runtime.

    Args:
        tags (List[str]): The list of tags to set.
    """
    Client().set_tags(tags)


def get_api_key() -> str:
    return Client().api_key


def set_parent_key(parent_key):
    """
    Set the parent API key which has visibility to projects it is parent to.

    Args:
        parent_key (str): The API key of the parent organization to set.
    """
    Client().set_parent_key(parent_key)


def stop_instrumenting():
    Client().stop_instrumenting()


@check_init
def create_agent(name: str, agent_id: Optional[str] = None):
    return Client().create_agent(name=name, agent_id=agent_id)
