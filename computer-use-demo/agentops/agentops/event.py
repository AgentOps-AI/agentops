"""
AgentOps events.

Data Class:
    Event: Represents discrete events to be recorded.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Union
from .helpers import get_ISO_time, check_call_stack_for_agent_id
from .enums import EventType
from uuid import UUID, uuid4
import traceback


@dataclass
class Event:
    """
    Abstract base class for events that will be recorded. Should not be instantiated directly.

    event_type(str): The type of event. Defined in enums.EventType. Some values are 'llm', 'action', 'api', 'tool', 'error'.
    params(dict, optional): The parameters of the function containing the triggered event, e.g. {'x': 1} in example below
    returns(str, optional): The return value of the function containing the triggered event, e.g. 2 in example below
    init_timestamp(str): A timestamp indicating when the event began. Defaults to the time when this Event was instantiated.
    end_timestamp(str): A timestamp indicating when the event ended. Defaults to the time when this Event was instantiated.
    agent_id(UUID, optional): The unique identifier of the agent that triggered the event.
    id(UUID): A unique identifier for the event. Defaults to a new UUID.

    foo(x=1) {
        ...
        // params equals {'x': 1}
        record(ActionEvent(params=**kwargs, ...))
        ...
        // returns equals 2
        return x+1
    }
    """

    event_type: EventType
    params: Optional[dict] = None
    returns: Optional[Union[str, List[str]]] = None
    init_timestamp: str = field(default_factory=get_ISO_time)
    end_timestamp: Optional[str] = None
    agent_id: Optional[UUID] = field(default_factory=check_call_stack_for_agent_id)
    id: UUID = field(default_factory=uuid4)


@dataclass
class ActionEvent(Event):
    """
    For generic events

    action_type(str, optional): High level name describing the action
    logs(str, optional): For detailed information/logging related to the action
    screenshot(str, optional): url to snapshot if agent interacts with UI
    """

    event_type: str = EventType.ACTION.value
    # TODO: Should not be optional, but non-default argument 'agent_id' follows default argument error
    action_type: Optional[str] = None
    logs: Optional[Union[str, Sequence[Any]]] = None
    screenshot: Optional[str] = None


@dataclass
class LLMEvent(Event):
    """
    For recording calls to LLMs. AgentOps auto-instruments calls to the most popular LLMs e.g. GPT, Claude, Gemini, etc.

    thread_id(UUID, optional): The unique identifier of the contextual thread that a message pertains to.
    prompt(str, list, optional): The message or messages that were used to prompt the LLM. Preferably in ChatML format which is more fully supported by AgentOps.
    prompt_tokens(int, optional): The number of tokens in the prompt message.
    completion(str, object, optional): The message or messages returned by the LLM. Preferably in ChatML format which is more fully supported by AgentOps.
    completion_tokens(int, optional): The number of tokens in the completion message.
    model(str, optional): LLM model e.g. "gpt-4", "gpt-3.5-turbo".

    """

    event_type: str = EventType.LLM.value
    thread_id: Optional[UUID] = None
    prompt: Optional[Union[str, List]] = None
    prompt_tokens: Optional[int] = None
    completion: Union[str, object] = None
    completion_tokens: Optional[int] = None
    model: Optional[str] = None


@dataclass
class ToolEvent(Event):
    """
    For recording calls to tools e.g. searchWeb, fetchFromDB

    name(str, optional): A name describing the tool or the actual function name if applicable e.g. searchWeb, fetchFromDB.
    logs(str, dict, optional): For detailed information/logging related to the tool.

    """

    event_type: str = EventType.TOOL.value
    name: Optional[str] = None
    logs: Optional[Union[str, dict]] = None


# Does not inherit from Event because error will (optionally) be linked to an ActionEvent, LLMEvent, etc that will have the details


@dataclass
class ErrorEvent:
    """
    For recording any errors e.g. ones related to agent execution

    trigger_event(Event, optional): The event object that triggered the error if applicable.
    exception(BaseException, optional): The thrown exception. We will automatically parse the error_type and details from this.
    error_type(str, optional): The type of error e.g. "ValueError".
    code(str, optional): A code that can be used to identify the error e.g. 501.
    details(str, optional): Detailed information about the error.
    logs(str, optional): For detailed information/logging related to the error.
    timestamp(str): A timestamp indicating when the error occurred. Defaults to the time when this ErrorEvent was instantiated.

    """

    trigger_event: Optional[Event] = None
    exception: Optional[BaseException] = None
    error_type: Optional[str] = None
    code: Optional[str] = None
    details: Optional[Union[str, Dict[str, str]]] = None
    logs: Optional[str] = field(default_factory=traceback.format_exc)
    timestamp: str = field(default_factory=get_ISO_time)

    def __post_init__(self):
        self.event_type = EventType.ERROR.value
        if self.exception:
            self.error_type = self.error_type or type(self.exception).__name__
            self.details = self.details or str(self.exception)
            self.exception = None  # removes exception from serialization
