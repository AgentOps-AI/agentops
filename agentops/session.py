from .helpers import get_ISO_time
from typing import Optional, List
from uuid import UUID


class Session:
    """
    Represents a session of events, with a start and end state.

    Args:
        session_id (UUID): The session id is used to record particular runs.
        tags (List[str], optional): Tags that can be used for grouping or sorting later. Examples could be ["GPT-4"].

    Attributes:
        init_timestamp (float): The timestamp for when the session started, represented as seconds since the epoch.
        end_timestamp (float, optional): The timestamp for when the session ended, represented as seconds since the epoch. This is only set after end_session is called.
        end_state (str, optional): The final state of the session. Suggested: "Success", "Fail", "Indeterminate"
        end_state_reason (str, optional): The reason for ending the session.

    """

    def __init__(
        self,
        session_id: UUID,
        tags: Optional[List[str]] = None,
        host_env: Optional[dict] = None,
    ):
        self.end_timestamp = None
        self.end_state: Optional[str] = None
        self.session_id = session_id
        self.init_timestamp = get_ISO_time()
        self.tags = tags
        self.video: Optional[str] = None
        self.end_state_reason: Optional[str] = None
        self.host_env = host_env

    def set_session_video(self, video: str) -> None:
        """
        Sets a url to the video recording of the session.

        Args:
            video (str): The url of the video recording
        """
        self.video = video

    def end_session(
        self, end_state: str = "Indeterminate", end_state_reason: Optional[str] = None
    ) -> None:
        """
        DEPRECATED
        End the session with a specified state, rating, and reason.

        Args:
            end_state (str, optional): The final state of the session. Options: "Success", "Fail", "Indeterminate"
            rating (str, optional): The rating for the session.
            end_state_reason (str, optional): The reason for ending the session. Provides context for why the session ended.
        """
        raise DeprecationWarning(
            "This function has been deprecated and will be removed. Please use agentops.end_session() and pass in the session_id parameter."
        )
