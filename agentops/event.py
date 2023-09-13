"""
AgentOps events.

Classes:
    Event: Represents discrete events to be recorded.
"""
from .helpers import get_ISO_time
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
        tags (List[str], optional): Tags that can be used for grouping or sorting later. e.g. ["GPT-4"].


    Attributes:
        timestamp (float): The timestamp for when the event was created, represented as seconds since the epoch.
    """

    def __init__(self, event_type: str,
                 params: Optional[str] = None,
                 returns: Optional[str] = None,
                 result: EventState = EventState.INDETERMINATE,
                 tags: Optional[List[str]] = None
                 ):
        self.event_type = event_type
        self.params = params
        self.returns = returns
        self.result = result
        self.tags = tags
        self.timestamp = get_ISO_time()
