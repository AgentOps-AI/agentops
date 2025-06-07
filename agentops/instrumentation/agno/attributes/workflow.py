"""Workflow attribute extraction for agno workflow instrumentation."""

from typing import Any, Dict, Optional, Tuple
from opentelemetry.util.types import AttributeValue

from agentops.semconv.instrumentation import InstrumentationAttributes
from agentops.semconv.span_kinds import SpanKind as AgentOpsSpanKind
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
            attributes["workflow.name"] = str(workflow.name)
        if hasattr(workflow, "workflow_id") and workflow.workflow_id:
            attributes["workflow.workflow_id"] = str(workflow.workflow_id)
        if hasattr(workflow, "description") and workflow.description:
            attributes["workflow.description"] = str(workflow.description)
        if hasattr(workflow, "app_id") and workflow.app_id:
            attributes["workflow.app_id"] = str(workflow.app_id)

        # Session and user attributes
        if hasattr(workflow, "session_id") and workflow.session_id:
            attributes["workflow.session_id"] = str(workflow.session_id)
        if hasattr(workflow, "session_name") and workflow.session_name:
            attributes["workflow.session_name"] = str(workflow.session_name)
        if hasattr(workflow, "user_id") and workflow.user_id:
            attributes["workflow.user_id"] = str(workflow.user_id)

        # Run-specific attributes
        if hasattr(workflow, "run_id") and workflow.run_id:
            attributes["workflow.run_id"] = str(workflow.run_id)

        # Configuration attributes
        if hasattr(workflow, "debug_mode"):
            attributes["workflow.debug_mode"] = bool(workflow.debug_mode)
        if hasattr(workflow, "monitoring"):
            attributes["workflow.monitoring"] = bool(workflow.monitoring)
        if hasattr(workflow, "telemetry"):
            attributes["workflow.telemetry"] = bool(workflow.telemetry)

        # Memory and storage attributes
        if hasattr(workflow, "memory") and workflow.memory:
            memory_type = type(workflow.memory).__name__
            attributes["workflow.memory.type"] = memory_type

        if hasattr(workflow, "storage") and workflow.storage:
            storage_type = type(workflow.storage).__name__
            attributes["workflow.storage.type"] = storage_type

        # Input parameters from kwargs
        if kwargs:
            # Count and types of input parameters
            attributes["workflow.input.parameter_count"] = len(kwargs)
            param_types = list(set(type(v).__name__ for v in kwargs.values()))
            if param_types:
                attributes["workflow.input.parameter_types"] = str(param_types)

            # Store specific input keys (without values for privacy)
            input_keys = list(kwargs.keys())
            if input_keys:
                attributes["workflow.input.parameter_keys"] = str(input_keys)

        # Workflow method parameters if available
        if hasattr(workflow, "_run_parameters") and workflow._run_parameters:
            param_count = len(workflow._run_parameters)
            attributes["workflow.method.parameter_count"] = param_count

        if hasattr(workflow, "_run_return_type") and workflow._run_return_type:
            attributes["workflow.method.return_type"] = str(workflow._run_return_type)

    # Process return value attributes
    if return_value is not None:
        return_type = type(return_value).__name__
        attributes["workflow.output.type"] = return_type

        # Handle RunResponse objects
        if hasattr(return_value, "content"):
            if hasattr(return_value, "content_type"):
                attributes["workflow.output.content_type"] = str(return_value.content_type)
            if hasattr(return_value, "event"):
                attributes["workflow.output.event"] = str(return_value.event)
            if hasattr(return_value, "model"):
                attributes["workflow.output.model"] = str(return_value.model) if return_value.model else ""
            if hasattr(return_value, "model_provider"):
                attributes["workflow.output.model_provider"] = (
                    str(return_value.model_provider) if return_value.model_provider else ""
                )

            # Count various response components
            if hasattr(return_value, "messages") and return_value.messages:
                attributes["workflow.output.message_count"] = len(return_value.messages)
            if hasattr(return_value, "tools") and return_value.tools:
                attributes["workflow.output.tool_count"] = len(return_value.tools)
            if hasattr(return_value, "images") and return_value.images:
                attributes["workflow.output.image_count"] = len(return_value.images)
            if hasattr(return_value, "videos") and return_value.videos:
                attributes["workflow.output.video_count"] = len(return_value.videos)
            if hasattr(return_value, "audio") and return_value.audio:
                attributes["workflow.output.audio_count"] = len(return_value.audio)

        # Handle generators/iterators
        elif hasattr(return_value, "__iter__") and not isinstance(return_value, (str, bytes)):
            attributes["workflow.output.is_streaming"] = True

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
            attributes["workflow.session.session_id"] = str(workflow.session_id)
        if hasattr(workflow, "session_name") and workflow.session_name:
            attributes["workflow.session.session_name"] = str(workflow.session_name)
        if hasattr(workflow, "workflow_id") and workflow.workflow_id:
            attributes["workflow.session.workflow_id"] = str(workflow.workflow_id)
        if hasattr(workflow, "user_id") and workflow.user_id:
            attributes["workflow.session.user_id"] = str(workflow.user_id)

        # Session state attributes
        if hasattr(workflow, "session_state") and workflow.session_state:
            if isinstance(workflow.session_state, dict):
                attributes["workflow.session.state_keys"] = str(list(workflow.session_state.keys()))
                attributes["workflow.session.state_size"] = len(workflow.session_state)

        # Storage attributes
        if hasattr(workflow, "storage") and workflow.storage:
            storage_type = type(workflow.storage).__name__
            attributes["workflow.session.storage_type"] = storage_type

    # Process session return value if it's a WorkflowSession
    if return_value is not None and hasattr(return_value, "session_id"):
        attributes["workflow.session.returned_session_id"] = str(return_value.session_id)
        if hasattr(return_value, "created_at") and return_value.created_at:
            attributes["workflow.session.created_at"] = int(return_value.created_at)
        if hasattr(return_value, "updated_at") and return_value.updated_at:
            attributes["workflow.session.updated_at"] = int(return_value.updated_at)

    # Set span kind - AgentOpsSpanKind.WORKFLOW is already a string
    attributes[InstrumentationAttributes.INSTRUMENTATION_TYPE] = AgentOpsSpanKind.WORKFLOW

    return attributes
