# agentops/__init__.py
from typing import Optional, List

from .client import Client
from .config import Configuration
from .event import ActionEvent, LLMEvent, ToolEvent, ErrorEvent, Event
from .event import Event, ActionEvent, LLMEvent, ToolEvent, ErrorEvent
from .enums import Models, LLMMessageFormat
from .decorators import record_function
from pydantic import Field


def init(api_key: Optional[str] = None,
         tags: Optional[List[str]] = None,
         endpoint: Optional[str] = None,
         max_wait_time: Optional[int] = 1000,
         max_queue_size: Optional[int] = 100,
         override=True,
         auto_start_session=True):
    Client(api_key, tags, endpoint, max_wait_time, max_queue_size, override, auto_start_session)


def end_session(end_state: str = Field("Indeterminate",
                                       description="End state of the session",
                                       pattern="^(Success|Fail|Indeterminate)$"),
                rating: Optional[str] = None,
                end_state_reason: Optional[str] = None,
                video: Optional[str] = None):
    Client().end_session(end_state, rating, end_state_reason, video)


def start_session(tags: Optional[List[str]] = None, config: Optional[Configuration] = None):
    Client().start_session(tags, config)


def record(event: Event):
    Client().record(event)


def add_tags(tags: List[str]):
    Client().add_tags(tags)


def set_tags(tags: List[str]):
    Client().set_tags(tags)
