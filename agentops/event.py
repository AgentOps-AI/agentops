from .helpers import get_ISO_time
from typing import Optional, Dict, Literal

"""
AgentOps events.

Classes:
    Event: Represents discrete events to be recorded.
    Session: Represents a session of events, with a start and end state.
"""


class Event:
    """
    Represents a discrete event to be recorded.

    Args:
        event_type (str): Type of the event, e.g., "API Call". Required.
        params (str, optional): The parameters passed to the operation.
        output (str, optional): The output of the operation.
        result (str, optional): Result of the operation, e.g., "success", "fail", "indeterminate".
        tags (Dict[str, str], optional): Tags that can be used for grouping or sorting later. e.g. {"llm": "GPT-4"}.


    Attributes:
        timestamp (float): The timestamp for when the event was created, represented as seconds since the epoch.
    """

    def __init__(self, event_type: str,
                 params: Optional[str] = None,
                 output: Optional[str] = None,
                 result: Optional[str] = None,
                 tags: Optional[Dict[str, str]] = None
                 ):
        self.event_type = event_type
        self.params = params
        self.output = output
        self.result = result
        self.tags = tags
        self.timestamp = get_ISO_time()


class Session:
    """
    Represents a session of events, with a start and end state.

    Args:
        session_id (str): The session id is used to record particular runs.
        tags (Dict[str, str], optional): Tags that can be used for grouping or sorting later. Examples could be {"llm": "GPT-4"}.

    Attributes:
        init_timestamp (float): The timestamp for when the session started, represented as seconds since the epoch.
        end_timestamp (float, optional): The timestamp for when the session ended, represented as seconds since the epoch. This is only set after end_session is called.
        end_state (str, optional): The final state of the session. Suggested: "Success", "Fail", "Indeterminate"
        rating (str, optional): The rating for the session.

    """

    def __init__(self, session_id: str, tags: Optional[Dict[str, str]] = None):
        self.session_id = session_id
        self.init_timestamp = get_ISO_time()
        self.tags = tags

    def end_session(self, end_state: Optional[str], rating: Optional[str] = None):
        """
        End the session with a specified state and rating.

        Args:
            end_state (str, optional): The final state of the session. Suggested: "Success", "Fail", "Indeterminate"
            rating (str, optional): The rating for the session.
        """
        self.end_state = end_state
        self.rating = rating
        self.end_timestamp = get_ISO_time()

    def get_session_id(self) -> str:
        """
        Get the session id.

        Returns:
            str: The id of the session.
        """
        return self.session_id

    def has_ended(self) -> str:
        """
        Returns whether the session has been ended

        Returns:
            bool: Whether the session has been ended
        """
        return hasattr(self, "end_state")
