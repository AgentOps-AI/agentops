"""
AgentOps events.

Classes:
    Event: Represents discrete events to be recorded.
"""
from .helpers import get_ISO_time, Models
from typing import Optional, List
from pydantic import Field


class Event:
    """
    Represents a discrete event to be recorded.

    Args:
        event_type (str): Type of the event, e.g., "API Call". Required.
        params (str, optional): The parameters passed to the operation.
        returns (str, optional): The output of the operation.
        result (str, optional): Result of the operation, e.g., "Success", "Fail", "Indeterminate". Defaults to "Indeterminate".
        action_type (str, optional): Type of action of the event e.g. 'action', 'llm', 'api'. Defaults to 'action'.
        model (Models, optional): The model used during the event if an LLM is used (i.e. GPT-4).
                For models, see the types available in the Models enum. 
                If a model is set but an action_type is not, the action_type will be coerced to 'llm'. 
                Defaults to None.
        prompt (str, optional): The input prompt for an LLM call when an LLM is being used. Defaults to None.
        tags (List[str], optional): Tags that can be used for grouping or sorting later. e.g. ["my_tag"]. Defaults to None.
        init_timestamp (float, optional): The timestamp for when the event was initiated, represented as seconds since the epoch.
                Defaults to the end timestamp.

    Attributes:
        event_type (str): Type of the event.
        params (str, optional): The parameters passed to the operation.
        returns (str, optional): The output of the operation.
        result (str): Result of the operation.
        action_type (str): Type of action of the event.
        model (Models, optional): The model used during the event.
        prompt (str, optional): The input prompt for an LLM call.
        tags (List[str], optional): Tags associated with the event.
        end_timestamp (float): The timestamp for when the event ended, represented as seconds since the epoch.
        init_timestamp (float): The timestamp for when the event was initiated, represented as seconds since the epoch.
    """

    def __init__(self, event_type: str,
                 params: Optional[str] = None,
                 returns: Optional[str] = None,
                 result: str = Field("Indeterminate",
                                     description="Result of the operation",
                                     pattern="^(Success|Fail|Indeterminate)$"),
                 action_type: Optional[str] = Field("action",
                                                    description="Type of action that the user is recording",
                                                    pattern="^(action|api|llm)$"),
                 model: Optional[Models] = None,
                 prompt: Optional[str] = None,
                 tags: Optional[List[str]] = None,
                 init_timestamp: Optional[float] = None
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
