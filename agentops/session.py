from .helpers import get_ISO_time
from pydantic import BaseModel, Field
from typing import Optional, List


class SessionState(BaseModel):
    end_state: str = Field(..., pattern="^(Success|Fail|Indeterminate)$")


class Session:
    """
    Represents a session of events, with a start and end state.

    Args:
        session_id (str): The session id is used to record particular runs.
        tags (List[str], optional): Tags that can be used for grouping or sorting later. Examples could be ["GPT-4"].

    Attributes:
        init_timestamp (float): The timestamp for when the session started, represented as seconds since the epoch.
        end_timestamp (float, optional): The timestamp for when the session ended, represented as seconds since the epoch. This is only set after end_session is called.
        end_state (str, optional): The final state of the session. Suggested: "Success", "Fail", "Indeterminate"
        rating (str, optional): The rating for the session.

    """

    def __init__(self, session_id: str, tags: Optional[List[str]] = None):
        self.session_id = session_id
        self.init_timestamp = get_ISO_time()
        self.tags = tags

    def end_session(self, end_state: str = "Indeterminate", rating: Optional[str] = None):
        """
        End the session with a specified state and rating.

        Args:
            end_state (str, optional): The final state of the session. Options: "Success", "Fail", "Indeterminate"
            rating (str, optional): The rating for the session.
        """
        SessionState(end_state=end_state)
        self.end_state = end_state
        self.rating = rating
        self.end_timestamp = get_ISO_time()

    @property
    def has_ended(self) -> bool:
        """
        Returns whether the session has been ended

        Returns:
            bool: Whether the session has been ended
        """
        return hasattr(self, "end_state")
