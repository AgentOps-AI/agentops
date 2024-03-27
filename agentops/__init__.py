# agentops/__init__.py
from os import environ
from typing import Optional, List

from .client import Client
from .config import Configuration
from .event import Event, ActionEvent, LLMEvent, ToolEvent, ErrorEvent
from .enums import Models
from .decorators import record_function
from pydantic import Field
from os import environ


def init(api_key: Optional[str] = None,
         parent_key: Optional[str] = None,
         tags: Optional[List[str]] = None,
         endpoint: Optional[str] = None,
         max_wait_time: Optional[int] = 1000,
         max_queue_size: Optional[int] = 100,
         override=True,
         auto_start_session=True):

    Client(api_key, parent_key, tags, endpoint, max_wait_time, max_queue_size, override, auto_start_session)


def end_session(end_state: str = Field("Indeterminate",
                                       description="End state of the session",
                                       pattern="^(Success|Fail|Indeterminate)$"),
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
