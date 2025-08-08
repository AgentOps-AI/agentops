from typing import Optional
from dataclasses import dataclass
from uuid import uuid4, UUID

from agentops.common import cache
from .environment import AUTH_SESSION_EXPIRY


def _make_key(session_id: str | UUID) -> str:
    """Generate a cache key for a session ID."""
    return f"agentops.session:{session_id}"


@dataclass
class Session:
    """
    User session management using a cache backend.

    This class provides methods for creating, retrieving, extending, and expiring
    user sessions, with each session associating a unique session ID with a user ID.
    Sessions are stored in the cache with a configurable expiry time (AUTH_SESSION_EXPIRY).

    Usage:
    ```python
    # Create a new session
    session = Session.create(user_id=user.id)

    # Get an existing session
    if session := Session.get(session_id):
        # Session is valid, user is authenticated
        user_id = session.user_id

    # Extend session expiry
    session.extend()

    # Log out by expiring the session
    session.expire()
    ```
    """

    session_id: UUID
    user_id: UUID

    @classmethod
    def get(cls, session_id: str | UUID) -> Optional['Session']:
        """
        Retrieve a session by its ID.

        Args:
            session_id (str | UUID): The session ID to look up

        Returns:
            Optional[Session]: Session object if found, None otherwise
        """
        session_id = str(session_id)
        if user_id := cache.get(_make_key(session_id)):
            return cls(
                session_id=UUID(session_id),
                user_id=UUID(user_id),
            )

        return None

    @classmethod
    def create(cls, user_id: UUID) -> 'Session':
        """
        Create a new session for a user.

        Args:
            user_id (UUID): The user ID to associate with the session

        Returns:
            Session: The newly created session
        """
        session = cls(uuid4(), user_id)
        cache.setex(_make_key(session.session_id), AUTH_SESSION_EXPIRY, str(session.user_id))
        return session

    def extend(self) -> None:
        """
        Extend the session's expiry time.

        Resets the expiry time to AUTH_SESSION_EXPIRY seconds from now.
        """
        return cache.expire(_make_key(self.session_id), AUTH_SESSION_EXPIRY)

    def expire(self) -> None:
        """
        Delete the session from the cache.

        Used for logout operations or to invalidate a session.
        """
        return cache.delete(_make_key(self.session_id))
