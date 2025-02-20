# agentops/__init__.py
import functools
import sys
import threading
from importlib.metadata import version as get_version
from typing import Any, Callable, List, Optional, Union, Unpack

import wrapt
from packaging import version

from agentops.api.session import SessionApiClient
from agentops.config import ConfigDict
from agentops.session.session import SessionState

from .client import Client
from .config import Config
from .helpers import check_agentops_update
from .session import Session

# Client global instance; one per process runtime
_client = Client()


def init(**kwargs: Unpack[ConfigDict]) -> Union[Session, None]:
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
        inherited_session_id (optional, str): Init Agentops with an existing Session
        skip_auto_end_session (optional, bool): Don't automatically end session based on your framework's decision-making
            (i.e. Crew determining when tasks are complete and ending the session)
    Attributes:
    """
    return _client.init(**kwargs)


def configure(**kwargs: Unpack[ConfigDict]):
    """Update client configuration"""
    _client.configure(**kwargs)


def start_session(
    tags: Optional[List[str]] = None
) -> Optional[Session]:
    """Start a new session for recording events.

    Args:
        tags (List[str], optional): Tags that can be used for grouping or sorting later.
            e.g. ["test_run"]

    Returns:
        Optional[Session]: Returns Session if successful, None otherwise.
    """
    return _client.start_session(tags)


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
