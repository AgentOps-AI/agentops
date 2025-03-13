"""Attributes specific to workflow spans."""


class WorkflowAttributes:
    """Workflow specific attributes."""

    # Workflow attributes
    WORKFLOW_NAME = "workflow.name"  # Name of the workflow
    WORKFLOW_TYPE = "workflow.type"  # Type of workflow
    WORKFLOW_INPUT = "workflow.input"  # Input to the workflow
    WORKFLOW_OUTPUT = "workflow.output"  # Output from the workflow
    MAX_TURNS = "workflow.max_turns"  # Maximum number of turns in a workflow
    FINAL_OUTPUT = "workflow.final_output"  # Final output of the workflow

    # Workflow step attributes
    WORKFLOW_STEP_TYPE = "workflow.step.type"  # Type of workflow step
    WORKFLOW_STEP_NAME = "workflow.step.name"  # Name of the workflow step
    WORKFLOW_STEP_INPUT = "workflow.step.input"  # Input to the workflow step
    WORKFLOW_STEP_OUTPUT = "workflow.step.output"  # Output from the workflow step
    WORKFLOW_STEP_STATUS = "workflow.step.status"  # Status of the workflow step
    WORKFLOW_STEP_ERROR = "workflow.step.error"  # Error from the workflow step
    WORKFLOW_STEP = "workflow.step"
