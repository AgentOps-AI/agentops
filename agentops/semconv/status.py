"""Status enumerations for spans."""

class Status:
    """Common status values."""
    
    SUCCESS = "success"
    ERROR = "error"
    IN_PROGRESS = "in_progress"
    CANCELLED = "cancelled"

class AgentStatus:
    """Agent status values."""
    
    INITIALIZED = "initialized"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"

class ToolStatus:
    """Tool status values."""
    
    CALLED = "called"
    EXECUTING = "executing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
