"""Session management module for AgentOps.

A session represents a single execution lifecycle of an agent or application, providing
tracking and monitoring capabilities. Sessions are the core building block for observability
in AgentOps. They can be configured to instrument LLM calls and other events, enhancing
observability through integration with instrumentation modules.

Key concepts:
    - A session begins when your application starts and ends when it completes
    - Multiple sessions can run concurrently
    - Each session has a unique ID and maintains its own state
    - Sessions track various metrics like LLM calls, tool usage, and errors
    - Sessions can be configured to instrument LLM calls, providing detailed analytics

Session States:
    - INITIALIZING: Session is being created and configured
    - RUNNING: Session is actively executing
    - SUCCEEDED: Session completed successfully
    - FAILED: Session ended with an error
    - INDETERMINATE: Session ended in an unclear state

Example usage:
    ```python
    from agentops import Session, Config
    
    # Create and start a new session
    config = Config(api_key="your-key")
    session = Session(session_id=uuid4(), config=config)
    
    # Add custom tags
    session.add_tags(["experiment-1", "production"])
    
    # Session automatically tracks events
    
    # End the session with a state
    session.end("SUCCEEDED", "Task completed successfully")
    ```

Working with multiple sessions:
    - Use get_active_sessions() to list all running sessions
    - Each session operates independently with its own state and metrics
    - Sessions can be retrieved by ID using get_session_by_id()
    - The default session (when only one exists) can be accessed via get_default_session()

Integration with Instrumentation:
    - Sessions can be configured to instrument LLM calls and other events
    - Integration with OpenTelemetry for enhanced tracing and observability

See also:
    - Session class for detailed session management
    - SessionState enum for possible session states
    - Registry functions for managing multiple sessions
"""

from .registry import add_session, get_active_sessions, remove_session
from .session import (Session, SessionState, session_ended, session_ending,
                      session_initialized, session_started, session_starting,
                      session_updated)

__all__ = [
    "Session",
    "SessionState",
    "get_active_sessions",
    "add_session",
    "remove_session",
    "session_initialized",
    "session_started",
    "session_starting",
    "session_ending",
    "session_ended",
    "session_updated"
]
