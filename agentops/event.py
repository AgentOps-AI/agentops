"""
AgentOps events.

Data Class:
    Event: Represents discrete events to be recorded.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from .helpers import get_ISO_time
from .enums import EventType, Models
from uuid import UUID


@dataclass
class Event:
    event_type: str  # EventType.ENUM.value
    tags: Optional[List[str]] = None
    init_timestamp: Optional[str] = field(default_factory=get_ISO_time)
    end_timestamp: str = field(default_factory=get_ISO_time)


@dataclass
class ActionEvent(Event):
    event_type: str = EventType.ACTION.value
    # TODO: Should not be optional, but non-default argument 'agent_id' follows default argument error
    agent_id: Optional[UUID] = None
    action_type: Optional[str] = None
    detail: Optional[str] = None
    logs: Optional[str] = None
    screenshot: Optional[str] = None

    # May be needed if we keep Optional for agent_id
    # def __post_init__(self):
    #     if self.agent_id is None:
    #         raise ValueError("agent_id is required for ActionEvent")


@dataclass
class ErrorEvent(Event):
    event_type: str = EventType.ERROR.value
    error_type: Optional[str] = None
    code: Optional[str] = None
    details: Optional[str] = None
    logs: Optional[str] = None


@dataclass
class LLMEvent(Event):
    event_type: str = EventType.LLM.value
    thread_id: Optional[UUID] = None
    model: Optional[Models] = None
    prompt: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


@dataclass
class ToolEvent(Event):
    event_type: str = EventType.TOOL.value
    agent_id: Optional[UUID] = None
    name: Optional[str] = None
    inputs: Optional[str] = None
    outputs: Optional[str] = None
    logs: Optional[str] = None
