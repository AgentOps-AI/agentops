# agentops/__init__.py
from os import environ
from typing import Optional, List

from .client import Client
from .config import Configuration
from .event import Event, ActionEvent, LLMEvent, ToolEvent, ErrorEvent
from .enums import Models
from .decorators import record_function
from .agent import track_agent


def init(api_key: Optional[str] = None,
         parent_key: Optional[str] = None,
         endpoint: Optional[str] = None,
         max_wait_time: Optional[int] = None,
         max_queue_size: Optional[int] = None,
         tags: Optional[List[str]] = None,
         override=True,
         auto_start_session=True):
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
            override (bool): Whether to override and LLM calls to emit as events.
            auto_start_session (bool): Whether to start a session automatically when the client is created.
        Attributes:
        """

    Client(api_key=api_key,
           parent_key=parent_key,
           endpoint=endpoint,
           max_wait_time=max_wait_time,
           max_queue_size=max_queue_size,
           tags=tags,
           override=override,
           auto_start_session=auto_start_session)


def end_session(end_state: str,
                end_state_reason: Optional[str] = None,
                video: Optional[str] = None):
    Client().end_session(end_state, end_state_reason, video)


def start_session(tags: Optional[List[str]] = None, config: Optional[Configuration] = None):
    Client().start_session(tags, config)


def record(event: Event):
    Client().record(event)


def add_tags(tags: List[str]):
    Client().add_tags(tags)


def set_tags(tags: List[str]):
    Client().set_tags(tags)


def get_api_key() -> str:
    return Client().api_key


def set_parent_key(parent_key):
    Client().set_parent_key(parent_key)
