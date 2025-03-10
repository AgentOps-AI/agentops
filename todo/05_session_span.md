# Task 5: Create SessionSpan Class

## Description
Implement the SessionSpan class that extends SpannedBase. This class will represent a session span, which is the root span for all operations in a session.

## Implementation Details

### File Location
`agentops/spans/session.py`

### Class Definition
```python
from __future__ import annotations

import datetime
import json
import threading
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from opentelemetry import context, trace
from opentelemetry.trace import Span, Status, StatusCode

from agentops.config import Config
from agentops.core import TracingCore
from agentops.logging import logger
from agentops.spanned import SpannedBase
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
        super().__init__(name=name, kind="session", parent=None, **kwargs)
        
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
        self.set_state(state)
        
        # Map state to status code
        status_code = StatusCode.OK
        if isinstance(state, str):
            if state.upper() in ("FAILED", "FAIL", "ERROR"):
                status_code = StatusCode.ERROR
            elif state.upper() in ("SUCCEEDED", "SUCCESS", "OK"):
                status_code = StatusCode.OK
            else:
                status_code = StatusCode.UNSET
        
        # End the span
        super().end(status_code)
        
        return self
    
    def set_state(self, state: str, reason: Optional[str] = None) -> None:
        """
        Set the session state.
        
        Args:
            state: New state
            reason: Optional reason for the state change
        """
        # Normalize state
        if isinstance(state, str):
            state = state.upper()
            if state in ("SUCCESS", "OK"):
                state = "SUCCEEDED"
            elif state in ("FAIL", "ERROR"):
                state = "FAILED"
        
        # Store state
        self._state = state
        self._state_reason = reason
        
        # Set as attribute
        state_str = state if reason is None else f"{state}({reason})"
        self.set_attribute("session.state", state_str)
        
        # Set status based on state
        if state == "SUCCEEDED":
            self.set_status(StatusCode.OK)
        elif state == "FAILED":
            self.set_status(StatusCode.ERROR, reason)
    
    @property
    def state(self) -> str:
        """Get the session state."""
        if self._state_reason:
            return f"{self._state}({self._state_reason})"
        return self._state
    
    @property
    def config(self) -> Config:
        """Get the session configuration."""
        return self._config
    
    @property
    def tags(self) -> List[str]:
        """Get the session tags."""
        return self._tags.copy()
    
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
        """Convert to dictionary."""
        result = super().to_dict()
        result.update({
            "config": self._config.dict(),
            "tags": self._tags,
            "host_env": self._host_env,
            "state": self.state,
        })
        return result
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), cls=AgentOpsJSONEncoder)
    
    def __str__(self) -> str:
        """String representation of the session span."""
        return f"SessionSpan(trace_id={self.trace_id}, state={self.state})"
```

## Dependencies
- Task 2: SpannedBase Abstract Class
- Task 4: Tracing Core
- OpenTelemetry SDK

## Testing Considerations
- Test session creation with different configurations
- Test state transitions
- Test tag management
- Test serialization to dictionary and JSON
- Test context 