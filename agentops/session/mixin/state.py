from typing import Optional, Union, Any

from opentelemetry.trace import Status, StatusCode

from agentops.logging import logger
from agentops.session.state import SessionState


class StateSessionMixin:
    """
    Mixin for handling session state management and transitions.
    
    This mixin encapsulates the legacy SessionState behavior for backwards compatibility.
    It handles state transitions, span status updates, and state attribute recording.
    """

    def __init__(self, **kwargs):
        # Initialize state
        self._state = SessionState.INITIALIZING
        self._state_reason = None
        
        # Continue with parent initialization
        super().__init__(**kwargs)

    @property
    def state(self) -> Union[SessionState, str]:
        """
        Get the current state with optional reason.
        
        This is legacy behavior maintained for backwards compatibility.
        """
        if self._state_reason:
            return f"{self._state}({self._state_reason})"
        return self._state

    @state.setter
    def state(self, value: Union[SessionState, str]) -> None:
        """
        Set the state and optionally update reason.
        
        This is legacy behavior maintained for backwards compatibility.
        """
        if isinstance(value, str):
            # Check if there's a reason in parentheses
            if "(" in value and value.endswith(")"):
                state_str, reason = value.split("(", 1)
                reason = reason.rstrip(")")
                self._state_reason = reason
                try:
                    self._state = SessionState.from_string(state_str)
                except ValueError:
                    logger.warning(f"Invalid session state: {state_str}")
                    self._state = SessionState.INDETERMINATE
                    self._state_reason = f"Invalid state: {state_str}"
            else:
                try:
                    self._state = SessionState.from_string(value)
                    self._state_reason = None
                except ValueError:
                    logger.warning(f"Invalid session state: {value}")
                    self._state = SessionState.INDETERMINATE
                    self._state_reason = f"Invalid state: {value}"
        else:
            self._state = value
            self._state_reason = None

        # Update span status if available
        self._update_span_status()
        
        # Record state as span attribute
        self._record_state_attribute()

    def _update_span_status(self) -> None:
        """
        Update the span status based on current state.
        
        This is legacy behavior maintained for backwards compatibility.
        """
        # Get the span safely using getattr
        span = getattr(self, "_span", None)
        if span is None:
            return
            
        if self._state == SessionState.SUCCEEDED:
            span.set_status(Status(StatusCode.OK))
        elif self._state == SessionState.FAILED:
            span.set_status(Status(StatusCode.ERROR))
        else:
            span.set_status(Status(StatusCode.UNSET))
    
    def _record_state_attribute(self) -> None:
        """
        Record the state as a span attribute.
        
        This is legacy behavior maintained for backwards compatibility.
        """
        # Get the span safely using getattr
        span = getattr(self, "_span", None)
        if span is None:
            return
            
        span.set_attribute("session.state", str(self.state))

    def set_state(self, state: Union[SessionState, str], reason: Optional[str] = None) -> None:
        """
        Set the state with an optional reason.
        
        This is legacy behavior maintained for backwards compatibility.
        """
        if isinstance(state, str):
            try:
                self._state = SessionState.from_string(state)
            except ValueError:
                logger.warning(f"Invalid session state: {state}")
                self._state = SessionState.INDETERMINATE
                self._state_reason = f"Invalid state: {state}"
        else:
            self._state = state
            
        self._state_reason = reason
        
        # Update span status and attributes
        self._update_span_status()
        self._record_state_attribute()

    def is_terminal(self) -> bool:
        """
        Check if the session is in a terminal state.
        
        This is legacy behavior maintained for backwards compatibility.
        """
        return self._state.is_terminal

    def is_alive(self) -> bool:
        """
        Check if the session is still active.
        
        This is legacy behavior maintained for backwards compatibility.
        """
        return self._state.is_alive 