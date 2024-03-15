"""
AgentOps events.

Data Class:
    Event: Represents discrete events to be recorded.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from .helpers import get_ISO_time
from .enums import EventType, Models, PromptMessageFormat
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
    prompt_messages: str | object = None
    prompt_messages_format: PromptMessageFormat = PromptMessageFormat.STRING
    # TODO: remove and just create it in __post_init__?
    _formatted_prompt_messages: object = field(init=False, default=None)
    completion: Optional[str] = None
    model: Optional[Models] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None

    def __post_init__(self):
        if self.prompt_messages_format == PromptMessageFormat.STRING:
            self._formatted_prompt_messages = {"type": "string", "string": self.prompt_messages}
        elif self.prompt_messages_format == PromptMessageFormat.CHATML:
            # Check if prompt_messages is already a list (indicating direct messages without "messages" key)
            if isinstance(self.prompt_messages, list):
                # Direct list of messages, add under "messages" key
                self._formatted_prompt_messages = {"type": "chatml", "messages": self.prompt_messages}
            elif "messages" in self.prompt_messages:
                # prompt_messages is a dict that includes a "messages" key
                self._formatted_prompt_messages = {"type": "chatml", **self.prompt_messages}
            else:
                logging.error("AgentOps: invalid prompt_messages format")


@dataclass
class ToolEvent(Event):
    event_type: str = EventType.TOOL.value
    agent_id: Optional[UUID] = None
    name: Optional[str] = None
    logs: Optional[str] = None


# Does not inherit from Event because error will (optionally) be linked to an ActionEvent, LLMEvent, etc that will have the details
@dataclass
class ErrorEvent():
    trigger_event: Optional[Event] = None
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
