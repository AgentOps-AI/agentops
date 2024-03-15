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
import logging


@dataclass
class Event:
    event_type: str  # EventType.ENUM.value
    params: Optional[str] = None
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
    prompt_messages: str | List = None  # TODO: remove from serialization
    prompt_messages_format: LLMMessageFormat = LLMMessageFormat.STRING  # TODO: remove from serialization
    # TODO: remove and just create it in __post_init__ so it can never be set by user?
    _formatted_prompt_messages: object = field(init=False, default=None)
    completion_message: str | object = None  # TODO: remove from serialization
    completion_message_format: LLMMessageFormat = LLMMessageFormat.STRING  # TODO: remove from serialization
    # TODO: remove and just create it in __post_init__ so it can never be set by user?
    _formatted_completion_message: object = field(init=False, default=None)
    model: Optional[Models] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None

    def __post_init__(self):
        # TODO should we just figure out if it's chatml so user doesn't have to pass anything?
        if self.prompt_messages_format == LLMMessageFormat.STRING:
            self._formatted_prompt_messages = {"type": "string", "string": self.prompt_messages}
        elif self.prompt_messages_format == LLMMessageFormat.CHATML:
            self._formatted_prompt_messages = {"type": "chatml", "messages": self.prompt_messages}

        if self.completion_message_format == LLMMessageFormat.STRING:
            self._formatted_completion_message = {"type": "string", "string": self.completion_message}
        elif self.completion_message_format == LLMMessageFormat.CHATML:
            self._formatted_completion_message = {"type": "chatml", "message": self.completion_message}

        # import pprint
        # import json
        # print("\n\_formatted_prompt_messages:\n")
        # pprint(self._formatted_prompt_messages)
        # print("\n\_formatted_completion_message:\n")
        # json.dump(self._formatted_completion_message)


@dataclass
class ToolEvent(Event):
    event_type: str = EventType.TOOL.value
    agent_id: Optional[UUID] = None
    name: Optional[str] = None
    logs: Optional[str] = None


# Does not inherit from Event because error will (optionally) be linked to an ActionEvent, LLMEvent, etc that will have the details
@dataclass
class ErrorEvent():
    trigger_event: Optional[Event] = None  # TODO: remove from serialization?
    error_type: Optional[str] = None
    code: Optional[str] = None
    details: Optional[str] = None
    logs: Optional[str] = None
    # event_type: str = EventType.ERROR.value # TODO: don't expose this
    event_type: str = field(init=False, default=EventType.ERROR.value)
    timestamp: str = field(default_factory=get_ISO_time)

    def __post_init__(self):
        if self.trigger_event:
            self.trigger_event_id = self.trigger_event.id
            self.trigger_event_type = self.trigger_event.event_type
            # TODO: remove trigger_event from serialization
            # e.g. field(repr=False, compare=False, hash=False, metadata={'serialize': False})
