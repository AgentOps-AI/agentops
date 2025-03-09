"""Attributes specific to workflow spans."""

class WorkflowAttributes:
    """Workflow specific attributes."""
    
    WORKFLOW_NAME = "workflow.name"        # Name of the workflow
    WORKFLOW_TYPE = "workflow.type"        # Type of workflow
    WORKFLOW_INPUT = "workflow.input"      # Input to the workflow
    WORKFLOW_OUTPUT = "workflow.output"    # Output from the workflow
    MAX_TURNS = "workflow.max_turns"       # Maximum number of turns in a workflow
    FINAL_OUTPUT = "workflow.final_output" # Final output of the workflow