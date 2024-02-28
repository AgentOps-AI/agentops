from ..event import Event
from typing import Dict

class LLM(Event):
    def __init__(self, session_id: str, thread_id: str, prompt: Dict, completion: Dict, model: str, cost: float, additional_param: str,prompt_tokens: Optional[int] = None,
                 completion_tokens: Optional[int] = None):
        super().__init__(event_type='llms', params={"prompt": prompt, "completion": completion}, model=model)
        self.session_id = session_id
        self.thread_id = thread_id
        self.cost = cost
        self.additional_param = additional_param
                self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
    
    def __str__(self):
        base_str = super().__str__()
        llms_details = {
            "session_id": self.session_id,
            "thread_id": self.thread_id,
            "cost": self.cost,
            "additional_param": self.additional_param,
        }
        return f"{base_str}, {llms_details}"