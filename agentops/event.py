"""
AgentOps events.

Classes:
    Event: Represents discrete events to be recorded.
"""
from .helpers import get_ISO_time
from typing import Optional, List, Dict, Any, TypedDict
from pydantic import Field


class ChatMLItem(TypedDict):
    role: str
    content: str


class MessageItem(TypedDict):
    content: str
    role: str
    function_call: Optional[str]
    tool_calls: Optional[str]


class ChoiceItem(TypedDict):
    finish_reason: str
    index: int
    message: MessageItem


class UsageItem(TypedDict):
    completion_tokens: int
    prompt_tokens: int
    total_tokens: int


class CompletionResponse(TypedDict):
    id: str
    choices: List[ChoiceItem]
    model: str
    type: str  # i.e. completion
    system_fingerprint: Optional[str]
    usage: Optional[UsageItem]


ChatML = List[ChatMLItem]


class Event:
    """
    Represents a discrete event to be recorded.
    """

    def __init__(self, event_type: str,
                 params: Optional[Dict[str, Any]] = None,
                 returns: Optional[Dict[str, Any]] = None,
                 result: str = Field("Indeterminate",
                                     description="Result of the operation",
                                     pattern="^(Success|Fail|Indeterminate)$"),
                 action_type: Optional[str] = Field("action",
                                                    description="Type of action that the user is recording",
                                                    pattern="^(action|api|llm|screenshot)$"),
                 model: Optional[str] = None,
                 prompt: Optional[str | ChatML] = None,
                 completion: Optional[CompletionResponse] = None,
                 tags: Optional[List[str]] = None,
                 init_timestamp: Optional[str] = None,
                 screenshot: Optional[str] = None,
                 prompt_tokens: Optional[int] = None,
                 completion_tokens: Optional[int] = None
                 ):
        self.event_type = event_type
        self.params = params
        self.returns = returns
        self.result = result
        self.tags = tags
        self.action_type = action_type
        self.model = model
        self.prompt = prompt
        self.completion = completion
        self.end_timestamp = get_ISO_time()
        self.init_timestamp = init_timestamp if init_timestamp else self.end_timestamp
        self.screenshot = screenshot
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens

    def __str__(self):
        return str({
            "event_type": self.event_type,
            "params": self.params,
            "returns": self.returns,
            "action_type": self.action_type,
            "result": self.result,
            "model": self.model,
            "prompt": self.prompt,
            "completion": self.completion,
            "tags": self.tags,
            "init_timestamp": self.init_timestamp,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
        })
