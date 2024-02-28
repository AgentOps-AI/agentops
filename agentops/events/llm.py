from ..event import Event, EventType, Models
from typing import Optional, Dict, Any


class LLMEvent(Event):
    def __init__(self,
                 model: Optional[Models] = None,
                 prompt: Optional[str] = None,
                 prompt_tokens: Optional[int] = None,
                 completion_tokens: Optional[int] = None,
                 **kwargs):
        super().__init__(event_type=EventType.llm, model=model, prompt=prompt, **kwargs)
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens

    def __str__(self):
        base_str = super().__str__()
        self_str = {
            "model": self.model,
            "prompt": self.prompt,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens
        }
        return str({**base_str, **self_str})
