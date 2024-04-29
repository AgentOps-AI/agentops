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

    def __init__(self, session_id: UUID, tags: Optional[List[str]] = None, host_env: Optional[dict] = None):
        self.end_timestamp = None
        self.end_state = None
        self.session_id = session_id
        self.init_timestamp = get_ISO_time()
        self.tags = tags
        self.video = None
        self.end_state_reason = None
        self.host_env = host_env

    def __setitem__(self, key, value):
        if key == 'end_timestamp':
            if not isinstance(value, str):
                raise ValueError("end_timestamp must be a string")
        elif key == 'end_state':
            if not isinstance(value, str):
                raise ValueError("end_state must be a string")
        elif key == 'session_id':
            if not isinstance(value, UUID):
                raise ValueError("session_id must be a UUID")
        elif key == 'init_timestamp':
            if not isinstance(value, str):
                raise ValueError("init_timestamp must be a string")
        elif key == 'tags':
            if not isinstance(value, list) or not all(isinstance(item,str) for item in value):
                raise ValueError("tags must be a list")
        elif key == 'video':
            if not isinstance(value, str):
                raise ValueError("video must be a string")
        elif key == 'end_state_reason':
            if not isinstance(value, str):
                raise ValueError("end_state_reason must be a string")
        elif key == 'host_env':
            if not isinstance(value, dict):
                raise ValueError("host_env must be a dictionary")

    def set_session_video(self, video: str):
        """
        Sets a url to the video recording of the session.

        Args:
            video (str): The url of the video recording
        """
        self.video = video

    def end_session(self, end_state: str = "Indeterminate", end_state_reason: Optional[str] = None):
        """
        End the session with a specified state, rating, and reason.

        Args:
            end_state (str, optional): The final state of the session. Options: "Success", "Fail", "Indeterminate"
            rating (str, optional): The rating for the session.
            end_state_reason (str, optional): The reason for ending the session. Provides context for why the session ended.
        """
        self.end_state = end_state
        self.end_state_reason = end_state_reason
        self.end_timestamp = get_ISO_time()

    @property
    def has_ended(self) -> bool:
        """
        Returns whether the session has been ended

        Returns:
            bool: Whether the session has been ended
        """
        return self.end_state is not None
