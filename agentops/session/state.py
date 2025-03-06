from dataclasses import field
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional, Union

from agentops.logging import logger


# Custom StrEnum implementation for Python < 3.11
class StrEnum(str, Enum):
    """String enum implementation for Python < 3.11"""

    def __str__(self) -> str:
        return self.value


if TYPE_CHECKING:
    from .session import Session


class SessionState(StrEnum):
    """Session state enumeration"""

    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    INDETERMINATE = "INITIALIZING"  # FIXME: Remove Backward compat. redundancy

    @property
    def is_terminal(self) -> bool:
        """Whether this is a terminal state"""
        return self in (self.FAILED, self.SUCCEEDED, self.INDETERMINATE)

    @property
    def is_alive(self) -> bool:
        """Whether the session is still active"""
        return self in (self.INITIALIZING, self.RUNNING)

    @classmethod
    def from_string(cls, state: str) -> "SessionState":
        """Convert string to SessionState, with simple aliases"""
        state = state.upper()
        if state in ("SUCCESS", "SUCCEEDED"):
            return cls.SUCCEEDED
        if state in ("FAIL", "FAILED"):
            return cls.FAILED
        try:
            return cls[state]  # Use direct lookup since it's a StrEnum
        except KeyError:
            return cls.INDETERMINATE


class SessionStateDescriptor:
    """Descriptor for managing session state with description"""

    def __init__(self, default_state: SessionState = SessionState.INITIALIZING):
        self._default = default_state

    def __set_name__(self, owner, name):
        self._state_name = f"_{name}"
        self._reason_name = f"_{name}_reason"

    def __get__(self, obj, objtype=None):
        """Get the current state"""
        if obj is None:
            return self._default

        state = getattr(obj, self._state_name, self._default)
        reason = getattr(obj, self._reason_name, None)

        if reason:
            return f"{state}({reason})"
        return state

    def __set__(self, obj: "Session", value: Union[SessionState, str]) -> None:
        """Set the state and optionally update reason"""
        if isinstance(value, str):
            try:
                state = SessionState.from_string(value)
            except ValueError:
                logger.warning(f"Invalid session state: {value}")
                state = SessionState.INDETERMINATE
                setattr(obj, self._reason_name, f"Invalid state: {value}")
        else:
            state = value

        setattr(obj, self._state_name, state)

        # Update span status if available
        if hasattr(obj, "span"):
            reason = getattr(obj, self._reason_name, None)
            obj.set_status(state, reason)
