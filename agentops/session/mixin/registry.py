from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from agentops.logging import logger
from agentops.session.registry import add_session, remove_session, set_current_session, get_current_session
from agentops.session.base import SessionBase

if TYPE_CHECKING:
    from agentops.session.session import Session


class SessionRegistryMixin(SessionBase):
    """
    Mixin that adds registry management functionality to a session.

    This mixin encapsulates the logic for registering and unregistering sessions
    from the global session registry, as well as managing the current session context.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the registry mixin."""
        # Call parent init
        super().__init__(*args, **kwargs)

    def _start_session_registry(self) -> None:
        """Register this session in the global registry and set as current."""
        # Register this session for cleanup
        add_session(self)

        # Set as current session
        set_current_session(self)

        logger.debug(f"[{self.session_id}] Session registered in registry")

    def _end_session_registry(self) -> None:
        """Unregister this session from the global registry."""
        # Unregister from cleanup
        remove_session(self)

        logger.debug(f"[{self.session_id}] Session unregistered from registry")

    @classmethod
    def get_current(cls) -> Optional["Session"]:
        """Get the current active session from the registry."""
        return get_current_session()
