from dataclasses import field
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional, Union, Any

from agentops.logging import logger


# Custom StrEnum implementation for Python < 3.11
class StrEnum(str, Enum):
    """String enum implementation for Python < 3.11"""

    def __str__(self) -> str:
        return self.value


if TYPE_CHECKING:
    from .session import Session
    from opentelemetry.trace import Span, Status, StatusCode


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


class SessionStateProperty:
    """
    Property descriptor for session state that acts as a mediator between
    state management and telemetry functionality.
    
    This descriptor handles:
    1. Setting and getting the session state
    2. Parsing state strings with optional reasons
    3. Updating span status based on state
    4. Recording state as span attribute
    """

    def __init__(self, default_state: SessionState = SessionState.INITIALIZING):
        self._default = default_state

    def __set_name__(self, owner, name):
        self._state_name = f"_{name}"
        self._reason_name = f"_{name}_reason"

    def __get__(self, obj, objtype=None):
        """Get the current state with optional reason"""
        if obj is None:
            return self._default

        state = getattr(obj, self._state_name, self._default)
        reason = getattr(obj, self._reason_name, None)

        if reason:
            return f"{state}({reason})"
        return state

    def __set__(self, obj, value: Union[SessionState, str]) -> None:
        """
        Set the state and handle telemetry updates.
        
        This method:
        1. Parses the state and reason from the value
        2. Sets the internal state and reason
        3. Updates the span status based on state
        4. Records the state as a span attribute
        """
        state = None
        reason = None

        # Parse the state and reason from the value
        if isinstance(value, str):
            # Check if there's a reason in parentheses
            if "(" in value and value.endswith(")"):
                state_str, reason_part = value.split("(", 1)
                reason = reason_part.rstrip(")")
                try:
                    state = SessionState.from_string(state_str)
                except ValueError:
                    logger.warning(f"Invalid session state: {state_str}")
                    state = SessionState.INDETERMINATE
                    reason = f"Invalid state: {state_str}"
            else:
                try:
                    state = SessionState.from_string(value)
                except ValueError:
                    logger.warning(f"Invalid session state: {value}")
                    state = SessionState.INDETERMINATE
                    reason = f"Invalid state: {value}"
        else:
            state = value

        # Set the internal state and reason
        setattr(obj, self._state_name, state)
        if reason:
            setattr(obj, self._reason_name, reason)
        else:
            # Clear any existing reason if not provided
            if hasattr(obj, self._reason_name):
                setattr(obj, self._reason_name, None)

        # Update span status and record state attribute
        self._update_span(obj, state, reason)

    def _update_span(self, obj: Any, state: SessionState, reason: Optional[str] = None) -> None:
        """
        Update span status and attributes based on state.
        
        This method:
        1. Gets the span from the object if available
        2. Updates the span status based on state
        3. Records the state as a span attribute
        4. Records the reason as a span attribute if provided
        """
        # Get the span from the object if available
        span = getattr(obj, "_span", None)
        if span is None:
            return

        # Import here to avoid circular imports
        from opentelemetry.trace import Status, StatusCode
            
        # Update span status based on state
        if state.is_terminal:
            if state == SessionState.SUCCEEDED:
                span.set_status(Status(StatusCode.OK))
            elif state == SessionState.FAILED:
                span.set_status(Status(StatusCode.ERROR))
            else:
                span.set_status(Status(StatusCode.UNSET))
                
        # Record state as span attribute
        span.set_attribute("session.state", str(self.__get__(obj)))
        
        # Add reason as attribute if present
        if reason:
            span.set_attribute("session.end_reason", reason)
