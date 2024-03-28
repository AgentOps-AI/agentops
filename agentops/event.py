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
    params: Optional[dict] = None
    returns: Optional[str] = None
    init_timestamp: Optional[str] = field(default_factory=get_ISO_time)
    end_timestamp: str = field(default_factory=get_ISO_time)
    id: UUID = field(default_factory=uuid4)
    # TODO: has_been_recorded: bool = False


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
    prompt_message: str | List = None
    prompt_tokens: Optional[int] = None
    completion_message: str | object = None
    completion_tokens: Optional[int] = None
    model: Optional[Models | str] = None


@dataclass
class ToolEvent(Event):
    event_type: str = EventType.TOOL.value
    agent_id: Optional[UUID] = None
    name: Optional[str] = None
    logs: Optional[str | dict] = None

# Does not inherit from Event because error will (optionally) be linked to an ActionEvent, LLMEvent, etc that will have the details


@dataclass
class ErrorEvent():
    trigger_event: Optional[Event] = None  # TODO: remove from serialization?
    error_type: Optional[str] = None
    code: Optional[str] = None
    details: Optional[str] = None
    logs: Optional[str] = None
    timestamp: str = field(default_factory=get_ISO_time)

    def __post_init__(self):
        self.event_type = EventType.ERROR.value
        if self.trigger_event:
            self.trigger_event_id = self.trigger_event.id
            self.trigger_event_type = self.trigger_event.event_type
            # TODO: remove trigger_event from serialization
            # e.g. field(repr=False, compare=False, hash=False, metadata={'serialize': False})
