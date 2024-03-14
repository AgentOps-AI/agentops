"""
AgentOps events.

Data Class:
    Event: Represents discrete events to be recorded.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from .helpers import get_ISO_time
from .enums import EventType, Models
from uuid import UUID, uuid4


@dataclass
class Event:
    event_type: str  # EventType.ENUM.value
    tags: Optional[List[str]] = None
    params: Optional[str] = None
    returns: Optional[str] = None
    init_timestamp: Optional[str] = field(default_factory=get_ISO_time)
    end_timestamp: str = field(default_factory=get_ISO_time)
    id: UUID = field(default_factory=uuid4)


@dataclass
class ActionEvent(Event):
    event_type: str = EventType.ACTION.value
    # TODO: Should not be optional, but non-default argument 'agent_id' follows default argument error
    agent_id: Optional[UUID] = None
    action_type: Optional[str] = None
    logs: Optional[str] = None
    screenshot: Optional[str] = None

    # May be needed if we keep Optional for agent_id
    # def __post_init__(self):
    #     if self.agent_id is None:
    #         raise ValueError("agent_id is required for ActionEvent")


@dataclass
class LLMEvent(Event):
    event_type: str = EventType.LLM.value
    agent_id: Optional[UUID] = None
    thread_id: Optional[UUID] = None
    prompt: Optional[str] = None
    completion: Optional[str] = None
    model: Optional[Models] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


@dataclass
class ToolEvent(Event):
    event_type: str = EventType.TOOL.value
    agent_id: Optional[UUID] = None
    name: Optional[str] = None
    logs: Optional[str] = None


####################
@dataclass
class Error():
    trigger_event_id: Optional[UUID]
    trigger_event_type: Optional[EventType]
    error_type: Optional[str] = None
    code: Optional[str] = None
    details: Optional[str] = None
    logs: Optional[str] = None
    timestamp: str = field(default_factory=get_ISO_time)

    def __init__(self, event: Event, **kwargs):
        self.trigger_event_id = event.id
        self.trigger_event_type = event.event_type
        for key, value in kwargs.items():
            setattr(self, key, value)
