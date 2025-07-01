"""Attributes specific to workflow spans."""


class WorkflowAttributes:
    """Workflow specific attributes."""

    # Core workflow attributes
    WORKFLOW_NAME = "workflow.name"  # Name of the workflow
    WORKFLOW_TYPE = "workflow.type"  # Type of workflow
    WORKFLOW_ID = "workflow.workflow_id"  # Unique identifier for the workflow instance
    WORKFLOW_RUN_ID = "workflow.run_id"  # Unique identifier for this workflow run
    WORKFLOW_DESCRIPTION = "workflow.description"  # Description of the workflow

    # Input/Output
    WORKFLOW_INPUT = "workflow.input"  # Input to the workflow
    WORKFLOW_INPUT_TYPE = "workflow.input.type"  # Type of input to the workflow
    WORKFLOW_OUTPUT = "workflow.output"  # Output from the workflow
    WORKFLOW_OUTPUT_TYPE = "workflow.output.type"  # Type of output from the workflow
    WORKFLOW_FINAL_OUTPUT = "workflow.final_output"  # Final output of the workflow

    # Workflow step attributes (only keep used ones)
    WORKFLOW_STEP_TYPE = "workflow.step.type"  # Type of workflow step
    WORKFLOW_STEP_STATUS = "workflow.step.status"  # Status of the workflow step

    # Configuration
    WORKFLOW_MAX_TURNS = "workflow.max_turns"  # Maximum number of turns in a workflow
    WORKFLOW_DEBUG_MODE = "workflow.debug_mode"  # Whether debug mode is enabled
    WORKFLOW_MONITORING = "workflow.monitoring"  # Whether monitoring is enabled
    WORKFLOW_TELEMETRY = "workflow.telemetry"  # Whether telemetry is enabled

    # Memory and Storage
    WORKFLOW_MEMORY_TYPE = "workflow.memory_type"  # Type of memory used by the workflow
    WORKFLOW_STORAGE_TYPE = "workflow.storage_type"  # Type of storage used by the workflow

    # Session context (simplified)
    WORKFLOW_SESSION_ID = "workflow.session_id"  # Session ID for the workflow execution
    WORKFLOW_SESSION_NAME = "workflow.session_name"  # Session name for the workflow
    WORKFLOW_USER_ID = "workflow.user_id"  # User ID associated with the workflow
    WORKFLOW_APP_ID = "workflow.app_id"  # Application ID associated with the workflow

    # Input metadata
    WORKFLOW_INPUT_PARAMETER_COUNT = "workflow.input.parameter_count"  # Number of input parameters
    WORKFLOW_INPUT_PARAMETER_KEYS = "workflow.input.parameter_keys"  # Keys of input parameters
    WORKFLOW_METHOD_PARAMETER_COUNT = "workflow.method.parameter_count"  # Number of method parameters
    WORKFLOW_METHOD_RETURN_TYPE = "workflow.method.return_type"  # Return type of the workflow method

    # Output metadata (commonly used)
    WORKFLOW_OUTPUT_CONTENT_TYPE = "workflow.output.content_type"  # Content type of the output
    WORKFLOW_OUTPUT_EVENT = "workflow.output.event"  # Event type of the output
    WORKFLOW_OUTPUT_MODEL = "workflow.output.model"  # Model used for the output
    WORKFLOW_OUTPUT_MODEL_PROVIDER = "workflow.output.model_provider"  # Model provider for the output
    WORKFLOW_OUTPUT_MESSAGE_COUNT = "workflow.output.message_count"  # Number of messages in output
    WORKFLOW_OUTPUT_TOOL_COUNT = "workflow.output.tool_count"  # Number of tools in output
    WORKFLOW_OUTPUT_IS_STREAMING = "workflow.output.is_streaming"  # Whether output is streaming

    # Media counts (used by agno)
    WORKFLOW_OUTPUT_IMAGE_COUNT = "workflow.output.image_count"  # Number of images in output
    WORKFLOW_OUTPUT_VIDEO_COUNT = "workflow.output.video_count"  # Number of videos in output
    WORKFLOW_OUTPUT_AUDIO_COUNT = "workflow.output.audio_count"  # Number of audio items in output

    # Session-specific attributes (used by agno)
    WORKFLOW_SESSION_WORKFLOW_ID = "workflow.session.workflow_id"  # Workflow ID in session context
    WORKFLOW_SESSION_USER_ID = "workflow.session.user_id"  # User ID in session context
    WORKFLOW_SESSION_STATE_KEYS = "workflow.session.state_keys"  # Keys in session state
    WORKFLOW_SESSION_STATE_SIZE = "workflow.session.state_size"  # Size of session state
    WORKFLOW_SESSION_STORAGE_TYPE = "workflow.session.storage_type"  # Storage type for session
    WORKFLOW_SESSION_RETURNED_SESSION_ID = "workflow.session.returned_session_id"  # Returned session ID
    WORKFLOW_SESSION_CREATED_AT = "workflow.session.created_at"  # Session creation timestamp
    WORKFLOW_SESSION_UPDATED_AT = "workflow.session.updated_at"  # Session update timestamp
