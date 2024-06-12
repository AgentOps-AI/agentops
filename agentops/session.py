from .helpers import get_ISO_time
from typing import Optional, List, Dict, Any
from uuid import UUID

class Session:
    """
    Represents a session of events, with a start and end state.

    Args:
        session_id (UUID): The session id is used to record particular runs.
        tags (List[str], optional): Tags that can be used for grouping or sorting later. Examples could be ["GPT-4"].
        host_env (dict, optional): Host environment details.

    Attributes:
        init_timestamp (float): The timestamp for when the session started, represented as seconds since the epoch.
        end_timestamp (float, optional): The timestamp for when the session ended, represented as seconds since the epoch. This is only set after end_session is called.
        end_state (str, optional): The final state of the session. Suggested: "Success", "Fail", "Indeterminate"
        end_state_reason (str, optional): The reason for ending the session.
        metadata (Dict[str, Any], optional): Additional metadata for the session.
        is_expired (bool): Flag indicating if the session has expired.
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
        self.metadata: Optional[Dict[str, Any]] = {}
        self.is_expired: bool = False

    def set_session_video(self, video: str) -> None:
        """
        Sets a url to the video recording of the session.

        Args:
            video (str): The url of the video recording
        """
        self.video = video

    def add_metadata(self, key: str, value: Any) -> None:
        """
        Adds metadata to the session.

        Args:
            key (str): The metadata key.
            value (Any): The metadata value.
        """
        if self.metadata is None:
            self.metadata = {}
        self.metadata[key] = value

    def end_session(
        self, end_state: str = "Indeterminate", end_state_reason: Optional[str] = None
    ) -> None:
        """
        End the session with a specified state and reason.

        Args:
            end_state (str, optional): The final state of the session. Options: "Success", "Fail", "Indeterminate"
            end_state_reason (str, optional): The reason for ending the session. Provides context for why the session ended.
        """
        self.end_state = end_state
        self.end_state_reason = end_state_reason
        self.end_timestamp = get_ISO_time()

    def expire_session(self) -> None:
        """
        Mark the session as expired.
        """
        self.is_expired = True
        self.end_session(end_state="Expired", end_state_reason="Session expired due to inactivity.")

    def validate_session(self) -> bool:
        """
        Validates the session attributes to ensure they meet certain criteria.

        Returns:
            bool: Whether the session is valid.
        """
        if not self.session_id or not isinstance(self.session_id, UUID):
            return False
        if not self.init_timestamp:
            return False
        return True

    @property
    def has_ended(self) -> bool:
        """
        Returns whether the session has been ended

        Returns:
            bool: Whether the session has been ended
        """
        return self.end_state is not None
