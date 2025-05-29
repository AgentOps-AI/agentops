"""
AgentOps enums for user-friendly API.

This module provides simple enums that users can import from agentops
without needing to know about OpenTelemetry internals.
"""

from enum import Enum
from opentelemetry.trace.status import StatusCode


class TraceState(Enum):
    """
    Enum for trace end states.

    This provides a user-friendly interface that maps to OpenTelemetry StatusCode internally.
    Users can simply use agentops.TraceState.SUCCESS instead of importing OpenTelemetry.
    """

    SUCCESS = StatusCode.OK
    ERROR = StatusCode.ERROR
    UNSET = StatusCode.UNSET

    def __str__(self) -> str:
        """Return the name for string representation."""
        return self.name

    def to_status_code(self) -> StatusCode:
        """Convert to OpenTelemetry StatusCode."""
        return self.value


# For backward compatibility, also provide these as module-level constants
SUCCESS = TraceState.SUCCESS
ERROR = TraceState.ERROR
UNSET = TraceState.UNSET
