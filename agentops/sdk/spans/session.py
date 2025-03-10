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
        
        return 