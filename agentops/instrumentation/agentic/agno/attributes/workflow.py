"""Workflow attribute extraction for agno workflow instrumentation."""

from typing import Any, Dict, Optional, Tuple
from opentelemetry.util.types import AttributeValue
import json

from agentops.semconv.instrumentation import InstrumentationAttributes
from agentops.semconv.span_kinds import SpanKind as AgentOpsSpanKind
from agentops.semconv.workflow import WorkflowAttributes
from agentops.instrumentation.common.attributes import get_common_attributes


def get_workflow_run_attributes(
    args: Tuple[Any, ...] = (),
    kwargs: Optional[Dict[str, Any]] = None,
    return_value: Optional[Any] = None,
) -> Dict[str, AttributeValue]:
    """Extract attributes from workflow run operations.

    Args:
        args: Positional arguments passed to the workflow run method
        kwargs: Keyword arguments passed to the workflow run method
        return_value: Return value from the workflow run method

    Returns:
        Dictionary of OpenTelemetry attributes for workflow runs
    """
    attributes = get_common_attributes()
    kwargs = kwargs or {}

    if args and len(args) > 0:
        workflow = args[0]

        # Core workflow attributes
        if hasattr(workflow, "name") and workflow.name:
            attributes[WorkflowAttributes.WORKFLOW_NAME] = str(workflow.name)
        if hasattr(workflow, "workflow_id") and workflow.workflow_id:
            attributes[WorkflowAttributes.WORKFLOW_ID] = str(workflow.workflow_id)
        if hasattr(workflow, "description") and workflow.description:
            attributes[WorkflowAttributes.WORKFLOW_DESCRIPTION] = str(workflow.description)
        if hasattr(workflow, "app_id") and workflow.app_id:
            attributes[WorkflowAttributes.WORKFLOW_APP_ID] = str(workflow.app_id)

        # Set workflow type
        attributes[WorkflowAttributes.WORKFLOW_TYPE] = "agno_workflow"

        # Session and user attributes
        if hasattr(workflow, "session_id") and workflow.session_id:
            attributes[WorkflowAttributes.WORKFLOW_SESSION_ID] = str(workflow.session_id)
        if hasattr(workflow, "session_name") and workflow.session_name:
            attributes[WorkflowAttributes.WORKFLOW_SESSION_NAME] = str(workflow.session_name)
        if hasattr(workflow, "user_id") and workflow.user_id:
            attributes[WorkflowAttributes.WORKFLOW_USER_ID] = str(workflow.user_id)

        # Run-specific attributes
        if hasattr(workflow, "run_id") and workflow.run_id:
            attributes[WorkflowAttributes.WORKFLOW_RUN_ID] = str(workflow.run_id)

        # Configuration attributes
        if hasattr(workflow, "debug_mode"):
            attributes[WorkflowAttributes.WORKFLOW_DEBUG_MODE] = bool(workflow.debug_mode)
        if hasattr(workflow, "monitoring"):
            attributes[WorkflowAttributes.WORKFLOW_MONITORING] = bool(workflow.monitoring)
        if hasattr(workflow, "telemetry"):
            attributes[WorkflowAttributes.WORKFLOW_TELEMETRY] = bool(workflow.telemetry)

        # Memory and storage attributes
        if hasattr(workflow, "memory") and workflow.memory:
            memory_type = type(workflow.memory).__name__
            attributes[WorkflowAttributes.WORKFLOW_MEMORY_TYPE] = memory_type

        if hasattr(workflow, "storage") and workflow.storage:
            storage_type = type(workflow.storage).__name__
            attributes[WorkflowAttributes.WORKFLOW_STORAGE_TYPE] = storage_type

        # Input parameters from kwargs
        if kwargs:
            # Store workflow input
            attributes[WorkflowAttributes.WORKFLOW_INPUT] = str(kwargs)

            # Count and types of input parameters
            attributes[WorkflowAttributes.WORKFLOW_INPUT_PARAMETER_COUNT] = len(kwargs)
            param_types = list(set(type(v).__name__ for v in kwargs.values()))
            if param_types:
                attributes[WorkflowAttributes.WORKFLOW_INPUT_TYPE] = str(param_types)

            # Store specific input keys (without values for privacy)
            input_keys = list(kwargs.keys())
            if input_keys:
                attributes[WorkflowAttributes.WORKFLOW_INPUT_PARAMETER_KEYS] = str(input_keys)

        # Workflow method parameters if available
        if hasattr(workflow, "_run_parameters") and workflow._run_parameters:
            param_count = len(workflow._run_parameters)
            attributes[WorkflowAttributes.WORKFLOW_METHOD_PARAMETER_COUNT] = param_count

        if hasattr(workflow, "_run_return_type") and workflow._run_return_type:
            attributes[WorkflowAttributes.WORKFLOW_METHOD_RETURN_TYPE] = str(workflow._run_return_type)

    # Process return value attributes
    if return_value is not None:
        return_type = type(return_value).__name__
        attributes[WorkflowAttributes.WORKFLOW_OUTPUT_TYPE] = return_type

        # Handle RunResponse objects
        if hasattr(return_value, "content"):
            # Store workflow output
            if return_value.content:
                attributes[WorkflowAttributes.WORKFLOW_OUTPUT] = str(return_value.content)

            if hasattr(return_value, "content_type"):
                attributes[WorkflowAttributes.WORKFLOW_OUTPUT_CONTENT_TYPE] = str(return_value.content_type)
            if hasattr(return_value, "event"):
                attributes[WorkflowAttributes.WORKFLOW_OUTPUT_EVENT] = str(return_value.event)
            if hasattr(return_value, "model"):
                attributes[WorkflowAttributes.WORKFLOW_OUTPUT_MODEL] = (
                    str(return_value.model) if return_value.model else ""
                )
            if hasattr(return_value, "model_provider"):
                attributes[WorkflowAttributes.WORKFLOW_OUTPUT_MODEL_PROVIDER] = (
                    str(return_value.model_provider) if return_value.model_provider else ""
                )

            # Count various response components
            if hasattr(return_value, "messages") and return_value.messages:
                attributes[WorkflowAttributes.WORKFLOW_OUTPUT_MESSAGE_COUNT] = len(return_value.messages)
            if hasattr(return_value, "tools") and return_value.tools:
                attributes[WorkflowAttributes.WORKFLOW_OUTPUT_TOOL_COUNT] = len(return_value.tools)
            if hasattr(return_value, "images") and return_value.images:
                attributes[WorkflowAttributes.WORKFLOW_OUTPUT_IMAGE_COUNT] = len(return_value.images)
            if hasattr(return_value, "videos") and return_value.videos:
                attributes[WorkflowAttributes.WORKFLOW_OUTPUT_VIDEO_COUNT] = len(return_value.videos)
            if hasattr(return_value, "audio") and return_value.audio:
                attributes[WorkflowAttributes.WORKFLOW_OUTPUT_AUDIO_COUNT] = len(return_value.audio)

        # Handle generators/iterators
        elif hasattr(return_value, "__iter__") and not isinstance(return_value, (str, bytes)):
            attributes[WorkflowAttributes.WORKFLOW_OUTPUT_IS_STREAMING] = True

    # Set span kind - AgentOpsSpanKind.WORKFLOW is already a string
    attributes[InstrumentationAttributes.INSTRUMENTATION_TYPE] = AgentOpsSpanKind.WORKFLOW

    return attributes


def get_workflow_session_attributes(
    args: Tuple[Any, ...] = (),
    kwargs: Optional[Dict[str, Any]] = None,
    return_value: Optional[Any] = None,
) -> Dict[str, AttributeValue]:
    """Extract attributes from workflow session operations.

    Args:
        args: Positional arguments passed to the session method
        kwargs: Keyword arguments passed to the session method
        return_value: Return value from the session method

    Returns:
        Dictionary of OpenTelemetry attributes for workflow sessions
    """
    attributes = get_common_attributes()
    kwargs = kwargs or {}

    if args and len(args) > 0:
        workflow = args[0]

        # Session attributes
        if hasattr(workflow, "session_id") and workflow.session_id:
            attributes[WorkflowAttributes.WORKFLOW_SESSION_ID] = str(workflow.session_id)
        if hasattr(workflow, "session_name") and workflow.session_name:
            attributes[WorkflowAttributes.WORKFLOW_SESSION_NAME] = str(workflow.session_name)
        if hasattr(workflow, "workflow_id") and workflow.workflow_id:
            attributes[WorkflowAttributes.WORKFLOW_SESSION_WORKFLOW_ID] = str(workflow.workflow_id)
        if hasattr(workflow, "user_id") and workflow.user_id:
            attributes[WorkflowAttributes.WORKFLOW_SESSION_USER_ID] = str(workflow.user_id)

        # Session state attributes
        if hasattr(workflow, "session_state") and workflow.session_state:
            if isinstance(workflow.session_state, dict):
                attributes[WorkflowAttributes.WORKFLOW_SESSION_STATE_KEYS] = str(list(workflow.session_state.keys()))
                attributes[WorkflowAttributes.WORKFLOW_SESSION_STATE_SIZE] = len(workflow.session_state)

        # Storage attributes
        if hasattr(workflow, "storage") and workflow.storage:
            storage_type = type(workflow.storage).__name__
            attributes[WorkflowAttributes.WORKFLOW_SESSION_STORAGE_TYPE] = storage_type

    # Process session return value if it's a WorkflowSession
    if return_value is not None and hasattr(return_value, "session_id"):
        attributes[WorkflowAttributes.WORKFLOW_SESSION_RETURNED_SESSION_ID] = str(return_value.session_id)
        if hasattr(return_value, "created_at") and return_value.created_at:
            attributes[WorkflowAttributes.WORKFLOW_SESSION_CREATED_AT] = int(return_value.created_at)
        if hasattr(return_value, "updated_at") and return_value.updated_at:
            attributes[WorkflowAttributes.WORKFLOW_SESSION_UPDATED_AT] = int(return_value.updated_at)

    # Set span kind - AgentOpsSpanKind.WORKFLOW is already a string
    attributes[InstrumentationAttributes.INSTRUMENTATION_TYPE] = AgentOpsSpanKind.WORKFLOW

    return attributes


def get_workflow_cache_attributes(
    args: Tuple[Any, ...] = (),
    kwargs: Optional[Dict[str, Any]] = None,
    return_value: Optional[Any] = None,
) -> Dict[str, AttributeValue]:
    """Extract attributes from workflow cache operations.

    Args:
        args: Positional arguments passed to the cache method
        kwargs: Keyword arguments passed to the cache method
        return_value: Return value from the cache method

    Returns:
        Dictionary of OpenTelemetry attributes for cache operations
    """
    attributes = get_common_attributes()
    kwargs = kwargs or {}

    if args and len(args) > 0:
        workflow = args[0]

        # Get workflow information
        if hasattr(workflow, "workflow_id") and workflow.workflow_id:
            attributes["cache.workflow_id"] = str(workflow.workflow_id)
        if hasattr(workflow, "session_id") and workflow.session_id:
            attributes["cache.session_id"] = str(workflow.session_id)

        # Get cache state
        if hasattr(workflow, "session_state") and isinstance(workflow.session_state, dict):
            attributes["cache.size"] = len(workflow.session_state)
            attributes["cache.keys"] = json.dumps(list(workflow.session_state.keys()))

    # Determine cache operation type and result
    if len(args) > 1:
        cache_key = str(args[1])
        attributes["cache.key"] = cache_key

    if return_value is not None:
        attributes["cache.hit"] = True
        attributes["cache.result"] = "hit"

        # Add value info
        if isinstance(return_value, str):
            attributes["cache.value_size"] = len(return_value)
            if len(return_value) <= 100:
                attributes["cache.value"] = return_value
            else:
                attributes["cache.value_preview"] = return_value[:100] + "..."
    else:
        attributes["cache.hit"] = False
        attributes["cache.result"] = "miss"

    return attributes
