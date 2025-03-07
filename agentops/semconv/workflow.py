"""Attributes specific to workflow spans."""

class WorkflowAttributes:
    """Attributes specific to workflow spans."""
    
    # Session
    SESSION_ID = "workflow.session_id"     # Session identifier
    SESSION_NAME = "workflow.session_name" # Session name
    
    # Workflow
    WORKFLOW_ID = "workflow.id"            # Workflow identifier
    WORKFLOW_NAME = "workflow.name"        # Workflow name
    WORKFLOW_TYPE = "workflow.type"        # Workflow type
    
    # Steps
    STEP_ID = "workflow.step.id"           # Step identifier
    STEP_NAME = "workflow.step.name"       # Step name
    STEP_INDEX = "workflow.step.index"     # Step index in sequence
    
    # Progress
    PROGRESS = "workflow.progress"         # Progress (0-100%)
    TOTAL_STEPS = "workflow.total_steps"   # Total number of steps
    CURRENT_STEP = "workflow.current_step" # Current step number
