from typing import Optional, Union

from agentops.session.base import SessionBase
from agentops.session.state import SessionState, SessionStateProperty

from .telemetry import TelemetrySessionMixin


class SessionStateMixin(TelemetrySessionMixin, SessionBase):
    """
    Mixin for handling session state management and transitions.

    This mixin encapsulates the legacy SessionState behavior for backwards compatibility.
    It handles state transitions, span status updates, and state attribute recording.
    """

    # Use the new property descriptor that acts as a mediator
    state = SessionStateProperty(SessionState.INITIALIZING)

    def _start_session_state(self) -> None:
        """
        Start method that updates state to RUNNING.

        This is legacy behavior maintained for backwards compatibility.
        """
        # Call parent start method to maintain the chain
        self.state = SessionState.RUNNING

    def _end_session_state(self, state: SessionState) -> None:
        """
        End method that updates state to a terminal state.

        This is legacy behavior maintained for backwards compatibility.
        """
        # Set the state if not already in a terminal state
        if not self.is_terminal():
            self.set_state(state)

    def set_state(self, state: Union[SessionState, str], reason: Optional[str] = None) -> None:
        """
        Set the state with an optional reason.

        This is legacy behavior maintained for backwards compatibility.
        """
        if reason:
            if isinstance(state, str):
                self.state = f"{state}({reason})"
            else:
                self.state = f"{state.value}({reason})"
        else:
            self.state = state

    def is_terminal(self) -> bool:
        """
        Check if the session is in a terminal state.

        This is legacy behavior maintained for backwards compatibility.
        """
        return self.state.is_terminal

    def is_alive(self) -> bool:
        """
        Check if the session is still active.

        This is legacy behavior maintained for backwards compatibility.
        """
        return self._state.is_alive

    # Legacy methods kept for backward compatibility
    def _update_span_status(self) -> None:
        """
        Update the span status based on current state.

        This is now handled by the SessionStateProperty but kept for backward compatibility.
        """
        # This is now handled by the SessionStateProperty
        pass

    def _record_state_attribute(self) -> None:
        """
        Record the state as a span attribute.

        This is now handled by the SessionStateProperty but kept for backward compatibility.
        """
        # This is now handled by the SessionStateProperty
        pass
