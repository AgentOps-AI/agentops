"""
AgentOps events.

Data Class:
    Event: Represents discrete events to be recorded.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from .helpers import get_ISO_time
from .enums import EventType, Models, LLMMessageFormat
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
    prompt: str | List = None  # TODO: remove from serialization
    prompt_format: LLMMessageFormat = LLMMessageFormat.STRING  # TODO: remove from serialization
    # TODO: remove and just create it in __post_init__ so it can never be set by user?
    _formatted_prompt: object = field(init=False, default=None)
    completion: str | object = None  # TODO: remove from serialization
    completion_format: LLMMessageFormat = LLMMessageFormat.STRING  # TODO: remove from serialization
    # TODO: remove and just create it in __post_init__ so it can never be set by user?
    _formatted_completion: object = field(init=False, default=None)
    model: Optional[Models | str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None

    def format_messages(self):
        if self.prompt:
            # TODO should we just figure out if it's chatml so user doesn't have to pass anything?
            if self.prompt_format == LLMMessageFormat.STRING:
                self._formatted_prompt = {"type": "string", "string": self.prompt}
            elif self.prompt_format == LLMMessageFormat.CHATML:
                self._formatted_prompt = {"type": "chatml", "messages": self.prompt}

        if self.completion:
            if self.completion_format == LLMMessageFormat.STRING:
                self._formatted_completion = {"type": "string", "string": self.completion}
            elif self.completion_format == LLMMessageFormat.CHATML:
                self._formatted_completion = {"type": "chatml", "message": self.completion}

    def __post_init__(self):
        # format if prompt/completion messages were passed when LLMEvent was created
        self.format_messages()


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
