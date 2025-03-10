from __future__ import annotations

import datetime
import json
import threading
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from opentelemetry import context, trace
from opentelemetry.trace import Span, Status, StatusCode

from agentops.config import Config
from agentops.sdk.core import TracingCore
from agentops.logging import logger
from agentops.sdk.spanned import SpannedBase
from agentops.helpers.serialization import AgentOpsJSONEncoder


class SessionSpan(SpannedBase):
    """
    Represents a session span, which is the root span for all operations in a session.
    
    A session span is always a root span (no parent) and serves as the master trace
    for all operations within the session.
    """
    
    def __init__(
        self,
        name: str,
        config: Config,
        tags: Optional[List[str]] = None,
        host_env: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Initialize a session span.
        
        Args:
            name: Name of the session
            config: Configuration for the session
            tags: Optional tags for the session
            host_env: Optional host environment information
            **kwargs: Additional keyword arguments
        """
        # Initialize tracing core with config
        core = TracingCore.get_instance()
        core.initialize(config)
        
        # Set default values
        kwargs.setdefault("kind", "session")
        
        # Initialize base class
        super().__init__(name=name, parent=None, **kwargs)
        
        # Store session-specific attributes
        self._config = config
        self._tags = tags or []
        self._host_env = host_env or {}
        self._state = "INITIALIZING"
        self._state_reason = None
        
        # Set attributes on span when started
        self._attributes.update({
            "session.name": name,
            "session.tags": self._tags,
            "session.state": self._state,
        })
        
        # Add host environment as attributes
        if self._host_env:
            for key, value in self._host_env.items():
                self._attributes[f"host.{key}"] = value
    
    def start(self) -> SessionSpan:
        """Start the session span."""
        if self._is_started:
            return self
        
        # Start the span
        super().start()
        
        # Update state
        self.set_state("RUNNING")
        
        return self
    
    def end(self, state: Union[str, StatusCode] = "SUCCEEDED") -> SessionSpan:
        """
        End the session span.
        
        Args:
            state: Final state of the session
        
        Returns:
            Self for chaining
        """
        if self._is_ended:
            return self
        
        # Set final state
        if isinstance(state, str):
            self.set_state(state)
        else:
            # If it's a StatusCode, map it to a state string
            if state == StatusCode.ERROR:
                self.set_state("FAILED")
            elif state == StatusCode.OK:
                self.set_state("SUCCEEDED")
            else:
                self.set_state("UNKNOWN")
        
        # Map state to status code
        status_code = StatusCode.OK
        if isinstance(state, str):
            if state.upper() in ("FAILED", "FAIL", "ERROR"):
                status_code = StatusCode.ERROR
            elif state.upper() in ("SUCCEEDED", "SUCCESS", "OK"):
                status_code = StatusCode.OK
            else:
                status_code = StatusCode.UNSET
        else:
            # If it's already a StatusCode, use it directly
            status_code = state
        
        # End the span
        super().end(status_code)
        
        return self
    
    def set_state(self, state: str, reason: Optional[str] = None) -> None:
        """
        Set the state of the session.
        
        Args:
            state: State of the session (e.g., "RUNNING", "FAILED", "SUCCEEDED")
            reason: Optional reason for the state
        """
        # Normalize state
        normalized_state = state.upper()
        if normalized_state in ("SUCCESS", "OK"):
            normalized_state = "SUCCEEDED"
        elif normalized_state in ("FAIL", "ERROR"):
            normalized_state = "FAILED"
        
        # Store state
        self._state = normalized_state
        self._state_reason = reason
        
        # Set attribute
        state_value = normalized_state
        if reason:
            state_value = f"{normalized_state}({reason})"
        self.set_attribute("session.state", state_value)
        
        # Set status if appropriate
        if normalized_state == "FAILED":
            self.set_status(StatusCode.ERROR, reason)
        elif normalized_state == "SUCCEEDED":
            self.set_status(StatusCode.OK)
    
    @property
    def state(self) -> str:
        """Get the state of the session."""
        if self._state_reason:
            return f"{self._state}({self._state_reason})"
        return self._state
    
    def add_tag(self, tag: str) -> None:
        """
        Add a tag to the session.
        
        Args:
            tag: Tag to add
        """
        if tag not in self._tags:
            self._tags.append(tag)
        self.set_attribute("session.tags", self._tags)
    
    def add_tags(self, tags: List[str]) -> None:
        """
        Add multiple tags to the session.
        
        Args:
            tags: Tags to add
        """
        for tag in tags:
            self.add_tag(tag)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the session span to a dictionary.
        
        Returns:
            Dictionary representation of the session span
        """
        result = {
            "name": self.name,
            "kind": self.kind,
            "trace_id": str(self.trace_id),
            "span_id": self.span_id,
            "state": self._state,
            "tags": self._tags,
        }
        
        if self._state_reason:
            result["state_reason"] = self._state_reason
        
        if self._start_time and isinstance(self._start_time, datetime.datetime):
            result["start_time"] = self._start_time.isoformat()
        
        if self._end_time and isinstance(self._end_time, datetime.datetime):
            result["end_time"] = self._end_time.isoformat()
            if isinstance(self._start_time, datetime.datetime):
                result["duration_ms"] = (self._end_time - self._start_time).total_seconds() * 1000
        
        return result 