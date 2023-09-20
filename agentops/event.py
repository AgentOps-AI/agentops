"""
AgentOps events.

Classes:
    Event: Represents discrete events to be recorded.
"""
from .helpers import get_ISO_time, ActionType, Models
from typing import Optional, List


class EventState:
    SUCCESS = "Success"
    FAIL = "Fail"
    INDETERMINATE = "Indeterminate"


class Event:
    """
    Represents a discrete event to be recorded.

    Args:
        event_type (str): Type of the event, e.g., "API Call". Required.
        params (str, optional): The parameters passed to the operation.
        returns (str, optional): The output of the operation.
        result (str, optional): Result of the operation, e.g., "Success", "Fail", "Indeterminate".
        action_type (ActionType, optional): Type of action of the evnet e.g. 'action', 'llm', 'api'
        model (Models, optional): The model used during the event if an LLM is used (i.e. GPT-4).
                For models, see the types available in the Models enum. 
                If a model is set but an action_type is not, the action_type will be coerced to 'llm'. 
                Defaults to None.
        prompt (str, optional): The input prompt for an LLM call when an LLM is being used.
        tags (List[str], optional): Tags that can be used for grouping or sorting later. e.g. ["my_tag"].


    Attributes:
        timestamp (float): The timestamp for when the event was created, represented as seconds since the epoch.
    """

    def __init__(self, event_type: str,
                 params: Optional[str] = None,
                 returns: Optional[str] = None,
                 result: EventState = EventState.INDETERMINATE,
                 action_type: Optional[ActionType] = ActionType.ACTION,
                 model: Optional[Models] = None,
                 prompt: Optional[str] = None,
                 tags: Optional[List[str]] = None
                 ):
        self.event_type = event_type
        self.params = params
        self.returns = returns
        self.result = result
        self.tags = tags
        self.action_type = action_type
        self.model = model
        self.prompt = prompt
        self.timestamp = get_ISO_time()
