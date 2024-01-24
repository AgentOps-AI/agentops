"""
AgentOps events.

Classes:
    Event: Represents discrete events to be recorded.
"""
from .helpers import get_ISO_time, Models
from typing import Optional, List, Dict, Any
from pydantic import Field


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
                 model: Optional[Models] = None,
                 prompt: Optional[str] = None,
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
            "tags": self.tags,
            "init_timestamp": self.init_timestamp,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
        })
