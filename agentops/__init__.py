# For backwards compatibility
from agentops.legacy import (
    start_session,
    end_session,
    track_agent,
    track_tool,
    end_all_sessions,
    Session,
    ToolEvent,
    ErrorEvent,
    ActionEvent,
    LLMEvent,
)  # type: ignore

# Import all required modules at the top
from opentelemetry.trace import get_current_span
from agentops.semconv import (
    AgentAttributes,
    ToolAttributes,
    WorkflowAttributes,
    CoreAttributes,
    SpanKind,
    SpanAttributes,
)
import json
from typing import List, Optional, Union, Dict, Any
from agentops.client import Client
from agentops.sdk.core import TraceContext, tracer
from agentops.sdk.decorators import trace, session, agent, task, workflow, operation, tool, guardrail, track_endpoint
from agentops.enums import TraceState, SUCCESS, ERROR, UNSET
from opentelemetry.trace.status import StatusCode

from agentops.logging.config import logger
from agentops.helpers.deprecation import deprecated, warn_deprecated_param
import threading

# Import validation functions
from agentops.validation import validate_trace_spans, print_validation_summary, ValidationError

# Thread-safe client management
_client_lock = threading.Lock()
_client = None


def get_client() -> Client:
    """Get the singleton client instance in a thread-safe manner"""
    global _client

    # Double-checked locking pattern for thread safety
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = Client()

    return _client


@deprecated("Automatically tracked in v4.")
def record(event):
    """
    Legacy function to record an event. This is kept for backward compatibility.

    In the current version, this simply sets the end_timestamp on the event.

    Args:
        event: The event to record
    """
    from agentops.helpers.time import get_ISO_time

    # TODO: Manual timestamp assignment is a temporary fix; should use proper event lifecycle
    if event and hasattr(event, "end_timestamp"):
        event.end_timestamp = get_ISO_time()

    return event


def init(
    api_key: Optional[str] = None,
    endpoint: Optional[str] = None,
    app_url: Optional[str] = None,
    max_wait_time: Optional[int] = None,
    max_queue_size: Optional[int] = None,
    tags: Optional[List[str]] = None,
    default_tags: Optional[List[str]] = None,
    trace_name: Optional[str] = None,
    instrument_llm_calls: Optional[bool] = None,
    auto_start_session: Optional[bool] = None,
    auto_init: Optional[bool] = None,
    skip_auto_end_session: Optional[bool] = None,
    env_data_opt_out: Optional[bool] = None,
    log_level: Optional[Union[str, int]] = None,
    fail_safe: Optional[bool] = None,
    log_session_replay_url: Optional[bool] = None,
    exporter_endpoint: Optional[str] = None,
    **kwargs,
):
    """
    Initializes the AgentOps SDK.

    Args:
        api_key (str, optional): API Key for AgentOps services. If none is provided, key will
            be read from the AGENTOPS_API_KEY environment variable.
        endpoint (str, optional): The endpoint for the AgentOps service. If none is provided, key will
            be read from the AGENTOPS_API_ENDPOINT environment variable. Defaults to 'https://api.agentops.ai'.
        app_url (str, optional): The dashboard URL for the AgentOps app. If none is provided, key will
            be read from the AGENTOPS_APP_URL environment variable. Defaults to 'https://app.agentops.ai'.
        max_wait_time (int, optional): The maximum time to wait in milliseconds before flushing the queue.
            Defaults to 5,000 (5 seconds)
        max_queue_size (int, optional): The maximum size of the event queue. Defaults to 512.
        tags (List[str], optional): [Deprecated] Use `default_tags` instead.
        default_tags (List[str], optional): Default tags for the sessions that can be used for grouping or sorting later (e.g. ["GPT-4"]).
        trace_name (str, optional): Name for the default trace/session. If none is provided, defaults to "default".
        instrument_llm_calls (bool): Whether to instrument LLM calls and emit LLMEvents.
        auto_start_session (bool): Whether to start a session automatically when the client is created.
        auto_init (bool): Whether to automatically initialize the client on import. Defaults to True.
        skip_auto_end_session (optional, bool): Don't automatically end session based on your framework's decision-making
            (i.e. Crew determining when tasks are complete and ending the session)
        env_data_opt_out (bool): Whether to opt out of collecting environment data.
        log_level (str, int): The log level to use for the client. Defaults to 'CRITICAL'.
        fail_safe (bool): Whether to suppress errors and continue execution when possible.
        log_session_replay_url (bool): Whether to log session replay URLs to the console. Defaults to True.
        exporter_endpoint (str, optional): Endpoint for the exporter. If none is provided, key will
            be read from the AGENTOPS_EXPORTER_ENDPOINT environment variable.
        **kwargs: Additional configuration parameters to be passed to the client.
    """
    global _client

    # Check for deprecated parameters and emit warnings
    if tags is not None:
        warn_deprecated_param("tags", "default_tags")

    # Merge tags and default_tags if both are provided
    merged_tags = None
    if tags and default_tags:
        merged_tags = list(set(tags + default_tags))
    elif tags:
        merged_tags = tags
    elif default_tags:
        merged_tags = default_tags

    # Check if in a Jupyter Notebook (manual start/end_trace())
    try:
        get_ipython().__class__.__name__ == "ZMQInteractiveShell"  # type: ignore
        auto_start_session = False
    except NameError:
        pass

    # Prepare initialization arguments
    init_kwargs = {
        "api_key": api_key,
        "endpoint": endpoint,
        "app_url": app_url,
        "max_wait_time": max_wait_time,
        "max_queue_size": max_queue_size,
        "default_tags": merged_tags,
        "trace_name": trace_name,
        "instrument_llm_calls": instrument_llm_calls,
        "auto_start_session": auto_start_session,
        "auto_init": auto_init,
        "skip_auto_end_session": skip_auto_end_session,
        "env_data_opt_out": env_data_opt_out,
        "log_level": log_level,
        "fail_safe": fail_safe,
        "log_session_replay_url": log_session_replay_url,
        "exporter_endpoint": exporter_endpoint,
        **kwargs,
    }

    # Get the current client instance (creates new one if needed)
    client = get_client()

    # Initialize the client directly
    return client.init(**init_kwargs)


def configure(**kwargs):
    """Update client configuration

    Args:
        **kwargs: Configuration parameters. Supported parameters include:
            - api_key: API Key for AgentOps services
            - endpoint: The endpoint for the AgentOps service
            - app_url: The dashboard URL for the AgentOps app
            - max_wait_time: Maximum time to wait in milliseconds before flushing the queue
            - max_queue_size: Maximum size of the event queue
            - default_tags: Default tags for the sessions
            - instrument_llm_calls: Whether to instrument LLM calls
            - auto_start_session: Whether to start a session automatically
            - skip_auto_end_session: Don't automatically end session
            - env_data_opt_out: Whether to opt out of collecting environment data
            - log_level: The log level to use for the client
            - fail_safe: Whether to suppress errors and continue execution
            - exporter: Custom span exporter for OpenTelemetry trace data
            - processor: Custom span processor for OpenTelemetry trace data
            - exporter_endpoint: Endpoint for the exporter
    """
    global _client

    # List of valid parameters that can be passed to configure
    valid_params = {
        "api_key",
        "endpoint",
        "app_url",
        "max_wait_time",
        "max_queue_size",
        "default_tags",
        "instrument_llm_calls",
        "auto_start_session",
        "skip_auto_end_session",
        "env_data_opt_out",
        "log_level",
        "fail_safe",
        "exporter",
        "processor",
        "exporter_endpoint",
    }

    # Check for invalid parameters
    invalid_params = set(kwargs.keys()) - valid_params
    if invalid_params:
        logger.warning(f"Invalid configuration parameters: {invalid_params}")

    client = get_client()
    client.configure(**kwargs)


def start_trace(
    trace_name: str = "session", tags: Optional[Union[Dict[str, Any], List[str]]] = None
) -> Optional[TraceContext]:
    """
    Starts a new trace (root span) and returns its context.
    This allows for multiple concurrent, user-managed traces.

    Args:
        trace_name: Name for the trace (e.g., "session", "my_custom_task").
        tags: Optional tags to attach to the trace span (list of strings or dict).

    Returns:
        A TraceContext object containing the span and context token, or None if SDK not initialized.
    """
    if not tracer.initialized:
        # Optionally, attempt to initialize the client if not already, or log a more severe warning.
        # For now, align with legacy start_session that would try to init.
        # However, explicit init is preferred before starting traces.
        logger.warning("AgentOps SDK not initialized. Attempting to initialize with defaults before starting trace.")
        try:
            init()  # Attempt to initialize with environment variables / defaults
            if not tracer.initialized:
                logger.error("SDK initialization failed. Cannot start trace.")
                return None
        except Exception as e:
            logger.error(f"SDK auto-initialization failed during start_trace: {e}. Cannot start trace.")
            return None

    return tracer.start_trace(trace_name=trace_name, tags=tags)


def end_trace(
    trace_context: Optional[TraceContext] = None, end_state: Union[TraceState, StatusCode, str] = TraceState.SUCCESS
) -> None:
    """
    Ends a trace (its root span) and finalizes it.
    If no trace_context is provided, ends all active session spans.

    Args:
        trace_context: The TraceContext object returned by start_trace. If None, ends all active traces.
        end_state: The final state of the trace (e.g., "Success", "Indeterminate", "Error").
    """
    if not tracer.initialized:
        logger.warning("AgentOps SDK not initialized. Cannot end trace.")
        return
    tracer.end_trace(trace_context=trace_context, end_state=end_state)


def update_trace_metadata(metadata: Dict[str, Any], prefix: str = "trace.metadata") -> bool:
    """
    Update metadata on the current running trace.

    Args:
        metadata: Dictionary of key-value pairs to set as trace metadata.
                 Values must be strings, numbers, booleans, or lists of these types.
                 Lists are converted to JSON string representation.
                 Keys can be either custom keys or semantic convention aliases.
        prefix: Prefix for metadata attributes (default: "trace.metadata").
               Ignored for semantic convention attributes.

    Returns:
        bool: True if metadata was successfully updated, False otherwise.

    """
    if not tracer.initialized:
        logger.warning("AgentOps SDK not initialized. Cannot update trace metadata.")
        return False

    # Build semantic convention mappings dynamically
    def build_semconv_mappings():
        """Build mappings from user-friendly keys to semantic convention attributes."""
        mappings = {}

        # Helper function to extract attribute name from semantic convention
        def extract_key_from_attr(attr_value: str) -> str:
            parts = attr_value.split(".")
            if len(parts) >= 2:
                # Handle special cases
                if parts[0] == "error":
                    # error.type -> error_type
                    return "_".join(parts)
                else:
                    # Default: entity.attribute -> entity_attribute
                    return "_".join(parts)
            return attr_value

        # Process each semantic convention class
        for cls in [AgentAttributes, ToolAttributes, WorkflowAttributes, CoreAttributes, SpanAttributes]:
            for attr_name, attr_value in cls.__dict__.items():
                if not attr_name.startswith("_") and isinstance(attr_value, str):
                    # Skip gen_ai attributes
                    if attr_value.startswith("gen_ai."):
                        continue

                    # Generate user-friendly key
                    user_key = extract_key_from_attr(attr_value)
                    mappings[user_key] = attr_value

                    # Add some additional convenience mappings
                    if attr_value == CoreAttributes.TAGS:
                        mappings["tags"] = attr_value

        return mappings

    # Build mappings if using semantic conventions
    SEMCONV_MAPPINGS = build_semconv_mappings()

    # Collect all valid semantic convention attributes
    VALID_SEMCONV_ATTRS = set()
    for cls in [AgentAttributes, ToolAttributes, WorkflowAttributes, CoreAttributes, SpanAttributes]:
        for key, value in cls.__dict__.items():
            if not key.startswith("_") and isinstance(value, str):
                # Include all attributes except gen_ai ones
                if not value.startswith("gen_ai."):
                    VALID_SEMCONV_ATTRS.add(value)

    # Find the current trace span
    span = None

    # Get the current span from OpenTelemetry context
    current_span = get_current_span()

    # Check if the current span is valid and recording
    if current_span and hasattr(current_span, "is_recording") and current_span.is_recording():
        # Check if this is a trace/session span or a child span
        span_name = getattr(current_span, "name", "")

        # If it's a session/trace span, use it directly
        if span_name.endswith(f".{SpanKind.SESSION}"):
            span = current_span
        else:
            # It's a child span, try to find the root trace span
            # Get all active traces
            active_traces = tracer.get_active_traces()
            if active_traces:
                # Find the trace that contains the current span
                current_trace_id = current_span.get_span_context().trace_id

                for trace_id_str, trace_ctx in active_traces.items():
                    try:
                        # Convert hex string back to int for comparison
                        trace_id = int(trace_id_str, 16)
                        if trace_id == current_trace_id:
                            span = trace_ctx.span
                            break
                    except (ValueError, AttributeError):
                        continue

                # If we couldn't find the parent trace, use the current span
                if not span:
                    span = current_span
            else:
                # No active traces, use the current span
                span = current_span

    # If no current span or it's not recording, check active traces
    if not span:
        active_traces = tracer.get_active_traces()
        if active_traces:
            # Get the most recently created trace (last in the dict)
            trace_context = list(active_traces.values())[-1]
            span = trace_context.span
            logger.debug("Using most recent active trace for metadata update")
        else:
            logger.warning("No active trace found. Cannot update metadata.")
            return False

    # Ensure the span is recording before updating
    if not span or (hasattr(span, "is_recording") and not span.is_recording()):
        logger.warning("Span is not recording. Cannot update metadata.")
        return False

    # Update the span attributes with the metadata
    try:
        updated_count = 0
        for key, value in metadata.items():
            # Validate the value type
            if value is None:
                continue

            # Convert lists to JSON string representation for OpenTelemetry compatibility
            if isinstance(value, list):
                # Ensure all list items are valid types
                if all(isinstance(item, (str, int, float, bool)) for item in value):
                    value = json.dumps(value)
                else:
                    logger.warning(f"Skipping metadata key '{key}': list contains invalid types")
                    continue
            elif not isinstance(value, (str, int, float, bool)):
                logger.warning(f"Skipping metadata key '{key}': value type {type(value)} not supported")
                continue

            # Determine the attribute key
            attribute_key = key

            # Check if key is already a valid semantic convention attribute
            if key in VALID_SEMCONV_ATTRS:
                # Key is already a valid semantic convention, use as-is
                attribute_key = key
            elif key in SEMCONV_MAPPINGS:
                # It's a user-friendly key, map it to semantic convention
                attribute_key = SEMCONV_MAPPINGS[key]
                logger.debug(f"Mapped '{key}' to semantic convention '{attribute_key}'")
            else:
                # Not a semantic convention, use with prefix
                attribute_key = f"{prefix}.{key}"

            # Set the attribute
            span.set_attribute(attribute_key, value)
            updated_count += 1

        if updated_count > 0:
            logger.debug(f"Successfully updated {updated_count} metadata attributes on trace")
            return True
        else:
            logger.warning("No valid metadata attributes were updated")
            return False

    except Exception as e:
        logger.error(f"Error updating trace metadata: {e}")
        return False


__all__ = [
    # Legacy exports
    "start_session",
    "end_session",
    "track_agent",
    "track_tool",
    "end_all_sessions",
    "Session",
    "ToolEvent",
    "ErrorEvent",
    "ActionEvent",
    "LLMEvent",
    # Modern exports
    "init",
    "start_trace",
    "end_trace",
    "update_trace_metadata",
    "Client",
    "get_client",
    # Decorators
    "trace",
    "session",
    "agent",
    "task",
    "workflow",
    "operation",
    "tool",
    "guardrail",
    "track_endpoint",
    # Enums
    "TraceState",
    "SUCCESS",
    "ERROR",
    "UNSET",
    # Validation
    "validate_trace_spans",
    "print_validation_summary",
    "ValidationError",
]
