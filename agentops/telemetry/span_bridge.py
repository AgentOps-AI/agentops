"""Bridge component to sync session properties with OpenTelemetry spans."""

from __future__ import annotations

from typing import TYPE_CHECKING
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

if TYPE_CHECKING:
    from agentops.session.session import Session, SessionState

class SessionSpanBridge:
    """Bridge between Session properties and OpenTelemetry spans."""
    
    def __init__(self, session: Session, root_span: trace.Span):
        self.session = session
        self.root_span = root_span
        
    def update_span_status(self, state: SessionState) -> None:
        """Update root span status based on session state."""
        if state.is_terminal:
            if state.name == "SUCCEEDED":
                self.root_span.set_status(Status(StatusCode.OK))
            elif state.name == "FAILED":
                self.root_span.set_status(Status(StatusCode.ERROR))
            else:
                self.root_span.set_status(Status(StatusCode.UNSET))
            
            if self.session.end_state_reason:
                self.root_span.set_attribute("session.end_reason", self.session.end_state_reason) 