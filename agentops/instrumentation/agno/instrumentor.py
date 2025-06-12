"""Agno Agent Instrumentation for AgentOps

This module provides instrumentation for the Agno Agent library, implementing OpenTelemetry
instrumentation for agent workflows and LLM model calls.

We focus on instrumenting the following key endpoints:
- Agent.run/arun - Main agent workflow execution (sync/async)
- Team._run/_arun - Team workflow execution (sync/async) 
- Team._run_stream/_arun_stream - Team streaming workflow execution (sync/async)
- FunctionCall.execute/aexecute - Tool execution when agents call tools (sync/async)
- Agent._run_tool/_arun_tool - Agent internal tool execution (sync/async)
- Agent._set_session_metrics - Session metrics capture for token usage and timing
- Workflow.run_workflow/arun_workflow - Workflow execution (sync/async)
- Workflow session management methods - Session lifecycle operations

This provides clean visibility into agent workflows and actual tool usage with proper 
parent-child span relationships.
"""

from typing import List, Collection, Any, Optional
from opentelemetry.trace import get_tracer
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.metrics import get_meter
from opentelemetry import trace, context as otel_context
from opentelemetry.trace import Status, StatusCode
from wrapt import wrap_function_wrapper
import threading

from agentops.logging import logger
from agentops.semconv import Meters
from agentops.instrumentation.common.wrappers import WrapConfig, wrap, unwrap

# Import attribute handlers
from agentops.instrumentation.agno.attributes.agent import get_agent_run_attributes
from agentops.instrumentation.agno.attributes.team import get_team_run_attributes
from agentops.instrumentation.agno.attributes.tool import get_tool_execution_attributes
from agentops.instrumentation.agno.attributes.metrics import get_metrics_attributes
from agentops.instrumentation.agno.attributes.workflow import (
    get_workflow_run_attributes,
    get_workflow_session_attributes,
)

# Library info for tracer/meter
LIBRARY_NAME = "agentops.instrumentation.agno"
LIBRARY_VERSION = "0.1.0"


class StreamingContextManager:
    """Manages span contexts for streaming agent and workflow executions."""

    def __init__(self):
        self._contexts = {}  # context_id -> (span_context, span)
        self._agent_sessions = {}  # session_id -> agent_id mapping for context lookup
        self._lock = threading.Lock()

    def store_context(self, context_id: str, span_context: Any, span: Any) -> None:
        """Store span context for streaming execution."""
        with self._lock:
            self._contexts[context_id] = (span_context, span)

    def get_context(self, context_id: str) -> Optional[tuple]:
        """Retrieve stored span context."""
        with self._lock:
            return self._contexts.get(context_id)

    def remove_context(self, context_id: str) -> None:
        """Remove stored context (when streaming completes)."""
        with self._lock:
            self._contexts.pop(context_id, None)

    def store_agent_session_mapping(self, session_id: str, agent_id: str) -> None:
        """Store mapping between session and agent for context lookup."""
        with self._lock:
            self._agent_sessions[session_id] = agent_id

    def get_agent_context_by_session(self, session_id: str) -> Optional[tuple]:
        """Get agent context using session ID."""
        with self._lock:
            agent_id = self._agent_sessions.get(session_id)
            if agent_id:
                return self._contexts.get(agent_id)
            return None

    def clear_all(self) -> None:
        """Clear all stored contexts."""
        with self._lock:
            self._contexts.clear()
            self._agent_sessions.clear()


# Global context manager instance
_streaming_context_manager = StreamingContextManager()


# Methods to wrap for instrumentation
WRAPPED_METHODS: List[WrapConfig] = [
    # Workflow session methods
    WrapConfig(
        trace_name="agno.workflow.session.load_session",
        package="agno.workflow.workflow",
        class_name="Workflow",
        method_name="load_session",
        handler=get_workflow_session_attributes,
    ),
    WrapConfig(
        trace_name="agno.workflow.session.new_session",
        package="agno.workflow.workflow",
        class_name="Workflow",
        method_name="new_session",
        handler=get_workflow_session_attributes,
    ),
    WrapConfig(
        trace_name="agno.workflow.session.read_from_storage",
        package="agno.workflow.workflow",
        class_name="Workflow",
        method_name="read_from_storage",
        handler=get_workflow_session_attributes,
    ),
    WrapConfig(
        trace_name="agno.workflow.session.write_to_storage",
        package="agno.workflow.workflow",
        class_name="Workflow",
        method_name="write_to_storage",
        handler=get_workflow_session_attributes,
    ),
]


class StreamingResultWrapper:
    """Wrapper for streaming results that maintains agent span as active throughout iteration."""

    def __init__(self, original_result, span, agent_id, agent_context):
        self.original_result = original_result
        self.span = span
        self.agent_id = agent_id
        self.agent_context = agent_context
        self._consumed = False

    def __iter__(self):
        """Return iterator that keeps agent span active during iteration."""
        context_token = otel_context.attach(self.agent_context)
        try:
            # Execute iteration within agent context
            for item in self.original_result:
                # Each item is yielded within the agent span context
                yield item
        finally:
            # Clean up when iteration is complete
            otel_context.detach(context_token)
            if not self._consumed:
                self._consumed = True
                self.span.end()
                _streaming_context_manager.remove_context(self.agent_id)

    def __getattr__(self, name):
        """Delegate attribute access to the original result."""
        return getattr(self.original_result, name)


def create_streaming_workflow_wrapper(tracer):
    """Create a streaming-aware wrapper for workflow run methods."""

    def wrapper(wrapped, instance, args, kwargs):
        # Get workflow ID for context storage
        workflow_id = getattr(instance, "workflow_id", None) or getattr(instance, "id", None) or id(instance)
        workflow_id = str(workflow_id)

        # Check if streaming is enabled
        is_streaming = kwargs.get("stream", getattr(instance, "stream", False))

        # For streaming, manually manage span lifecycle
        if is_streaming:
            span = tracer.start_span("agno.workflow.run.workflow")

            try:
                # Set workflow attributes
                attributes = get_workflow_run_attributes(args=(instance,) + args, kwargs=kwargs)
                for key, value in attributes.items():
                    span.set_attribute(key, value)

                # Store context for streaming - capture current context with active span
                current_context = trace.set_span_in_context(span, otel_context.get_current())
                _streaming_context_manager.store_context(workflow_id, current_context, span)

                # Execute the original function within workflow context
                context_token = otel_context.attach(current_context)
                try:
                    result = wrapped(*args, **kwargs)
                finally:
                    otel_context.detach(context_token)

                # Set result attributes
                result_attributes = get_workflow_run_attributes(
                    args=(instance,) + args, kwargs=kwargs, return_value=result
                )
                for key, value in result_attributes.items():
                    if key not in attributes:  # Avoid duplicates
                        span.set_attribute(key, value)

                span.set_status(Status(StatusCode.OK))

                # For streaming results, we need to keep the span open
                # The span will be closed when streaming completes
                return result

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                span.end()
                _streaming_context_manager.remove_context(workflow_id)
                raise
        else:
            # For non-streaming, use normal context manager
            with tracer.start_as_current_span("agno.workflow.run.workflow") as span:
                try:
                    # Set workflow attributes
                    attributes = get_workflow_run_attributes(args=(instance,) + args, kwargs=kwargs)
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                    # Execute the original function
                    result = wrapped(*args, **kwargs)

                    # Set result attributes
                    result_attributes = get_workflow_run_attributes(
                        args=(instance,) + args, kwargs=kwargs, return_value=result
                    )
                    for key, value in result_attributes.items():
                        if key not in attributes:  # Avoid duplicates
                            span.set_attribute(key, value)

                    span.set_status(Status(StatusCode.OK))
                    return result

                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

    return wrapper


def create_streaming_workflow_async_wrapper(tracer):
    """Create a streaming-aware async wrapper for workflow run methods."""

    async def wrapper(wrapped, instance, args, kwargs):
        # Get workflow ID for context storage
        workflow_id = getattr(instance, "workflow_id", None) or getattr(instance, "id", None) or id(instance)
        workflow_id = str(workflow_id)

        # Check if streaming is enabled
        is_streaming = kwargs.get("stream", getattr(instance, "stream", False))

        # For streaming, manually manage span lifecycle
        if is_streaming:
            span = tracer.start_span("agno.workflow.run.workflow")

            try:
                # Set workflow attributes
                attributes = get_workflow_run_attributes(args=(instance,) + args, kwargs=kwargs)
                for key, value in attributes.items():
                    span.set_attribute(key, value)

                # Store context for streaming - capture current context with active span
                current_context = trace.set_span_in_context(span, otel_context.get_current())
                _streaming_context_manager.store_context(workflow_id, current_context, span)

                # Execute the original function within workflow context
                context_token = otel_context.attach(current_context)
                try:
                    result = await wrapped(*args, **kwargs)
                finally:
                    otel_context.detach(context_token)

                # Set result attributes
                result_attributes = get_workflow_run_attributes(
                    args=(instance,) + args, kwargs=kwargs, return_value=result
                )
                for key, value in result_attributes.items():
                    if key not in attributes:  # Avoid duplicates
                        span.set_attribute(key, value)

                span.set_status(Status(StatusCode.OK))

                # For streaming results, we need to keep the span open
                # The span will be closed when streaming completes
                return result

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                span.end()
                _streaming_context_manager.remove_context(workflow_id)
                raise
        else:
            # For non-streaming, use normal context manager
            with tracer.start_as_current_span("agno.workflow.run.workflow") as span:
                try:
                    # Set workflow attributes
                    attributes = get_workflow_run_attributes(args=(instance,) + args, kwargs=kwargs)
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                    # Execute the original function
                    result = await wrapped(*args, **kwargs)

                    # Set result attributes
                    result_attributes = get_workflow_run_attributes(
                        args=(instance,) + args, kwargs=kwargs, return_value=result
                    )
                    for key, value in result_attributes.items():
                        if key not in attributes:  # Avoid duplicates
                            span.set_attribute(key, value)

                    span.set_status(Status(StatusCode.OK))
                    return result

                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

    return wrapper


def create_streaming_agent_wrapper(tracer):
    """Create a streaming-aware wrapper for agent run methods."""

    def wrapper(wrapped, instance, args, kwargs):
        # Get agent ID for context storage
        agent_id = getattr(instance, "agent_id", None) or getattr(instance, "id", None) or id(instance)
        agent_id = str(agent_id)

        # Get session ID for context mapping
        session_id = getattr(instance, "session_id", None)

        # Check if streaming is enabled
        is_streaming = kwargs.get("stream", getattr(instance, "stream", False))

        # For streaming, manually manage span lifecycle
        if is_streaming:
            span = tracer.start_span("agno.agent.run.agent")

            try:
                # Set agent attributes
                attributes = get_agent_run_attributes(args=(instance,) + args, kwargs=kwargs)
                for key, value in attributes.items():
                    span.set_attribute(key, value)

                # Store context for streaming - capture current context with active span
                current_context = trace.set_span_in_context(span, otel_context.get_current())
                _streaming_context_manager.store_context(agent_id, current_context, span)

                # Store session-to-agent mapping for LLM context lookup
                if session_id:
                    _streaming_context_manager.store_agent_session_mapping(session_id, agent_id)

                # Execute the original function within agent context
                context_token = otel_context.attach(current_context)
                try:
                    result = wrapped(*args, **kwargs)
                finally:
                    otel_context.detach(context_token)

                # Set result attributes
                result_attributes = get_agent_run_attributes(
                    args=(instance,) + args, kwargs=kwargs, return_value=result
                )
                for key, value in result_attributes.items():
                    if key not in attributes:  # Avoid duplicates
                        span.set_attribute(key, value)

                span.set_status(Status(StatusCode.OK))

                # Wrap the result to maintain context and end span when complete
                if hasattr(result, "__iter__"):
                    return StreamingResultWrapper(result, span, agent_id, current_context)
                else:
                    # Not actually streaming, clean up immediately
                    span.end()
                    _streaming_context_manager.remove_context(agent_id)
                    return result

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                span.end()
                _streaming_context_manager.remove_context(agent_id)
                raise
        else:
            # For non-streaming, use normal context manager
            with tracer.start_as_current_span("agno.agent.run.agent") as span:
                try:
                    # Set agent attributes
                    attributes = get_agent_run_attributes(args=(instance,) + args, kwargs=kwargs)
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                    # Execute the original function
                    result = wrapped(*args, **kwargs)

                    # Set result attributes
                    result_attributes = get_agent_run_attributes(
                        args=(instance,) + args, kwargs=kwargs, return_value=result
                    )
                    for key, value in result_attributes.items():
                        if key not in attributes:  # Avoid duplicates
                            span.set_attribute(key, value)

                    span.set_status(Status(StatusCode.OK))
                    return result

                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

    return wrapper


def create_streaming_agent_async_wrapper(tracer):
    """Create a streaming-aware async wrapper for agent run methods."""

    async def wrapper(wrapped, instance, args, kwargs):
        # Get agent ID for context storage
        agent_id = getattr(instance, "agent_id", None) or getattr(instance, "id", None) or id(instance)
        agent_id = str(agent_id)

        # Get session ID for context mapping
        session_id = getattr(instance, "session_id", None)

        # Check if streaming is enabled
        is_streaming = kwargs.get("stream", getattr(instance, "stream", False))

        # For streaming, manually manage span lifecycle
        if is_streaming:
            span = tracer.start_span("agno.agent.run.agent")

            try:
                # Set agent attributes
                attributes = get_agent_run_attributes(args=(instance,) + args, kwargs=kwargs)
                for key, value in attributes.items():
                    span.set_attribute(key, value)

                # Store context for streaming - capture current context with active span
                current_context = trace.set_span_in_context(span, otel_context.get_current())
                _streaming_context_manager.store_context(agent_id, current_context, span)

                # Store session-to-agent mapping for LLM context lookup
                if session_id:
                    _streaming_context_manager.store_agent_session_mapping(session_id, agent_id)

                # Execute the original function within agent context
                context_token = otel_context.attach(current_context)
                try:
                    result = await wrapped(*args, **kwargs)
                finally:
                    otel_context.detach(context_token)

                # Set result attributes
                result_attributes = get_agent_run_attributes(
                    args=(instance,) + args, kwargs=kwargs, return_value=result
                )
                for key, value in result_attributes.items():
                    if key not in attributes:  # Avoid duplicates
                        span.set_attribute(key, value)

                span.set_status(Status(StatusCode.OK))

                # Wrap the result to maintain context and end span when complete
                if hasattr(result, "__iter__"):
                    return StreamingResultWrapper(result, span, agent_id, current_context)
                else:
                    # Not actually streaming, clean up immediately
                    span.end()
                    _streaming_context_manager.remove_context(agent_id)
                    return result

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                span.end()
                _streaming_context_manager.remove_context(agent_id)
                raise
        else:
            # For non-streaming, use normal context manager
            with tracer.start_as_current_span("agno.agent.run.agent") as span:
                try:
                    # Set agent attributes
                    attributes = get_agent_run_attributes(args=(instance,) + args, kwargs=kwargs)
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                    # Execute the original function
                    result = await wrapped(*args, **kwargs)

                    # Set result attributes
                    result_attributes = get_agent_run_attributes(
                        args=(instance,) + args, kwargs=kwargs, return_value=result
                    )
                    for key, value in result_attributes.items():
                        if key not in attributes:  # Avoid duplicates
                            span.set_attribute(key, value)

                    span.set_status(Status(StatusCode.OK))
                    return result

                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

    return wrapper


def create_streaming_tool_wrapper(tracer):
    """Create a streaming-aware wrapper for tool execution methods."""

    def wrapper(wrapped, instance, args, kwargs):
        # Try to find the agent or workflow context for proper span hierarchy
        parent_context = None
        parent_span = None

        # Try to get context from agent
        try:
            if hasattr(instance, "_agent"):
                agent = instance._agent
                agent_id = getattr(agent, "agent_id", None) or getattr(agent, "id", None) or id(agent)
                agent_id = str(agent_id)
                context_info = _streaming_context_manager.get_context(agent_id)
                if context_info:
                    parent_context, parent_span = context_info
        except Exception:
            pass  # Continue without agent context if not found

        # Try to get context from workflow if agent context not found
        if not parent_context:
            try:
                if hasattr(instance, "_workflow"):
                    workflow = instance._workflow
                    workflow_id = (
                        getattr(workflow, "workflow_id", None) or getattr(workflow, "id", None) or id(workflow)
                    )
                    workflow_id = str(workflow_id)
                    context_info = _streaming_context_manager.get_context(workflow_id)
                    if context_info:
                        parent_context, parent_span = context_info
            except Exception:
                pass  # Continue without workflow context if not found

        # Use parent context if available, otherwise use current context
        if parent_context:
            context_token = otel_context.attach(parent_context)
            try:
                with tracer.start_as_current_span("agno.tool.execute.tool_usage") as span:
                    try:
                        # Set tool attributes
                        attributes = get_tool_execution_attributes(args=(instance,) + args, kwargs=kwargs)
                        for key, value in attributes.items():
                            span.set_attribute(key, value)

                        # Execute the original function
                        result = wrapped(*args, **kwargs)

                        # Set result attributes
                        result_attributes = get_tool_execution_attributes(
                            args=(instance,) + args, kwargs=kwargs, return_value=result
                        )
                        for key, value in result_attributes.items():
                            if key not in attributes:  # Avoid duplicates
                                span.set_attribute(key, value)

                        span.set_status(Status(StatusCode.OK))
                        return result

                    except Exception as e:
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        span.record_exception(e)
                        raise
            finally:
                otel_context.detach(context_token)
        else:
            # Fallback to normal span creation
            with tracer.start_as_current_span("agno.tool.execute.tool_usage") as span:
                try:
                    # Set tool attributes
                    attributes = get_tool_execution_attributes(args=(instance,) + args, kwargs=kwargs)
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                    # Execute the original function
                    result = wrapped(*args, **kwargs)

                    # Set result attributes
                    result_attributes = get_tool_execution_attributes(
                        args=(instance,) + args, kwargs=kwargs, return_value=result
                    )
                    for key, value in result_attributes.items():
                        if key not in attributes:  # Avoid duplicates
                            span.set_attribute(key, value)

                    span.set_status(Status(StatusCode.OK))
                    return result

                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

    return wrapper


def create_metrics_wrapper(tracer):
    """Create a wrapper for metrics methods with dynamic span naming."""

    def wrapper(wrapped, instance, args, kwargs):
        # Extract model ID for dynamic span naming
        span_name = "agno.agent.metrics"  # fallback
        if hasattr(instance, "model") and instance.model and hasattr(instance.model, "id"):
            model_id = str(instance.model.id)
            span_name = f"{model_id}.llm"

        with tracer.start_as_current_span(span_name) as span:
            try:
                # Set attributes
                attributes = get_metrics_attributes(args=(instance,) + args, kwargs=kwargs)
                for key, value in attributes.items():
                    span.set_attribute(key, value)

                # Execute the original function
                result = wrapped(*args, **kwargs)

                # Set result attributes
                result_attributes = get_metrics_attributes(args=(instance,) + args, kwargs=kwargs, return_value=result)
                for key, value in result_attributes.items():
                    if key not in attributes:  # Avoid duplicates
                        span.set_attribute(key, value)

                span.set_status(Status(StatusCode.OK))
                return result

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    return wrapper


def create_team_internal_wrapper(tracer):
    """Create a wrapper for Team internal methods (_run/_arun) that manages team span lifecycle."""

    def wrapper(wrapped, instance, args, kwargs):
        # Get team ID for context storage
        team_id = getattr(instance, "team_id", None) or getattr(instance, "id", None) or id(instance)
        team_id = str(team_id)

        # Check if we already have a team context (from print_response)
        existing_context = _streaming_context_manager.get_context(team_id)

        if existing_context:
            # We're being called from print_response, use existing context
            parent_context, parent_span = existing_context

            # Execute within the existing team context
            context_token = otel_context.attach(parent_context)
            try:
                with tracer.start_as_current_span("agno.team.run.workflow") as span:
                    try:
                        # Set workflow attributes
                        attributes = get_team_run_attributes(args=(instance,) + args, kwargs=kwargs)
                        for key, value in attributes.items():
                            span.set_attribute(key, value)

                        # Execute the original function
                        result = wrapped(*args, **kwargs)

                        span.set_status(Status(StatusCode.OK))
                        return result

                    except Exception as e:
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        span.record_exception(e)
                        raise
                    finally:
                        # Close the parent team span when workflow completes
                        if parent_span:
                            parent_span.end()
                            _streaming_context_manager.remove_context(team_id)
            finally:
                otel_context.detach(context_token)
        else:
            # Direct call to _run, create new team span
            with tracer.start_as_current_span("agno.team.run.workflow") as span:
                try:
                    # Set workflow attributes
                    attributes = get_team_run_attributes(args=(instance,) + args, kwargs=kwargs)
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                    # Execute the original function
                    result = wrapped(*args, **kwargs)

                    span.set_status(Status(StatusCode.OK))
                    return result

                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

    return wrapper


def create_team_internal_async_wrapper(tracer):
    """Create an async wrapper for Team internal methods (_arun) that manages team span lifecycle."""

    async def wrapper(wrapped, instance, args, kwargs):
        # Get team ID for context storage
        team_id = getattr(instance, "team_id", None) or getattr(instance, "id", None) or id(instance)
        team_id = str(team_id)

        # Check if we already have a team context (from print_response)
        existing_context = _streaming_context_manager.get_context(team_id)

        if existing_context:
            # We're being called from print_response, use existing context
            parent_context, parent_span = existing_context

            # Execute within the existing team context
            context_token = otel_context.attach(parent_context)
            try:
                with tracer.start_as_current_span("agno.team.run.workflow") as span:
                    try:
                        # Set workflow attributes
                        attributes = get_team_run_attributes(args=(instance,) + args, kwargs=kwargs)
                        for key, value in attributes.items():
                            span.set_attribute(key, value)

                        # Execute the original function
                        result = await wrapped(*args, **kwargs)

                        span.set_status(Status(StatusCode.OK))
                        return result

                    except Exception as e:
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        span.record_exception(e)
                        raise
                    finally:
                        # Close the parent team span when workflow completes
                        if parent_span:
                            parent_span.end()
                            _streaming_context_manager.remove_context(team_id)
            finally:
                otel_context.detach(context_token)
        else:
            # Direct call to _arun, create new team span
            with tracer.start_as_current_span("agno.team.run.workflow") as span:
                try:
                    # Set workflow attributes
                    attributes = get_team_run_attributes(args=(instance,) + args, kwargs=kwargs)
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                    # Execute the original function
                    result = await wrapped(*args, **kwargs)

                    span.set_status(Status(StatusCode.OK))
                    return result

                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

    return wrapper


def create_team_wrapper(tracer):
    """Create a wrapper for Team methods that establishes the team context."""

    def wrapper(wrapped, instance, args, kwargs):
        # Get team ID for context storage
        team_id = getattr(instance, "team_id", None) or getattr(instance, "id", None) or id(instance)
        team_id = str(team_id)

        # Check if streaming is enabled
        is_streaming = kwargs.get("stream", getattr(instance, "stream", False))

        # For print_response, we need to wrap the internal _run method instead
        # because print_response returns immediately
        if wrapped.__name__ == "print_response":
            # Create team span but don't manage it here
            span = tracer.start_span("agno.team.run.agent")

            try:
                # Set team attributes
                attributes = get_team_run_attributes(args=(instance,) + args, kwargs=kwargs)
                for key, value in attributes.items():
                    span.set_attribute(key, value)

                # Store context for child spans
                current_context = trace.set_span_in_context(span, otel_context.get_current())
                _streaming_context_manager.store_context(team_id, current_context, span)

                # The span will be closed by the internal _run method
                # Just execute print_response normally
                result = wrapped(*args, **kwargs)
                return result

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                span.end()
                _streaming_context_manager.remove_context(team_id)
                raise
        else:
            # For run/arun methods, use standard span management
            span = tracer.start_span("agno.team.run.agent")

            try:
                # Set team attributes
                attributes = get_team_run_attributes(args=(instance,) + args, kwargs=kwargs)
                for key, value in attributes.items():
                    span.set_attribute(key, value)

                # Store context for child spans
                current_context = trace.set_span_in_context(span, otel_context.get_current())
                _streaming_context_manager.store_context(team_id, current_context, span)

                # Execute the original function within team context
                context_token = otel_context.attach(current_context)
                try:
                    result = wrapped(*args, **kwargs)

                    # For streaming results, wrap them to keep span alive
                    if is_streaming and hasattr(result, "__iter__"):
                        return StreamingResultWrapper(result, span, team_id, current_context)
                    else:
                        # Non-streaming, close span
                        span.end()
                        _streaming_context_manager.remove_context(team_id)
                        return result

                finally:
                    otel_context.detach(context_token)

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                span.end()
                _streaming_context_manager.remove_context(team_id)
                raise

    return wrapper


def create_team_async_wrapper(tracer):
    """Create an async wrapper for Team methods that establishes the team context."""

    async def wrapper(wrapped, instance, args, kwargs):
        # Get team ID for context storage
        team_id = getattr(instance, "team_id", None) or getattr(instance, "id", None) or id(instance)
        team_id = str(team_id)

        # Check if streaming is enabled
        is_streaming = kwargs.get("stream", getattr(instance, "stream", False))

        # Create team span
        span = tracer.start_span("agno.team.run.agent")

        try:
            # Set team attributes
            attributes = get_team_run_attributes(args=(instance,) + args, kwargs=kwargs)
            for key, value in attributes.items():
                span.set_attribute(key, value)

            # Store context for child spans - capture current context with active span
            current_context = trace.set_span_in_context(span, otel_context.get_current())
            _streaming_context_manager.store_context(team_id, current_context, span)

            # Execute the original function within team context
            context_token = otel_context.attach(current_context)
            try:
                result = await wrapped(*args, **kwargs)

                # For non-streaming, close the span
                if not is_streaming:
                    span.end()
                    _streaming_context_manager.remove_context(team_id)

                return result
            finally:
                otel_context.detach(context_token)

        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            span.end()
            _streaming_context_manager.remove_context(team_id)
            raise

    return wrapper


def get_agent_context_for_llm():
    """Helper function for LLM instrumentation to get current agent context."""
    current_context = otel_context.get_current()
    current_span = trace.get_current_span(current_context)

    # Check if we're already in an agent span
    if current_span and hasattr(current_span, "name") and "agent" in current_span.name:
        return current_context, current_span

    # Try to find stored agent context by checking active contexts
    # This is a fallback for cases where context isn't properly propagated
    return None, None


class AgnoInstrumentor(BaseInstrumentor):
    """Agno instrumentation class."""

    def instrumentation_dependencies(self) -> Collection[str]:
        """Returns list of packages required for instrumentation."""
        return ["agno >= 0.1.0"]

    def _instrument(self, **kwargs):
        """Install instrumentation for Agno."""
        tracer_provider = kwargs.get("tracer_provider")
        tracer = get_tracer(LIBRARY_NAME, LIBRARY_VERSION, tracer_provider)

        meter_provider = kwargs.get("meter_provider")
        meter = get_meter(LIBRARY_NAME, LIBRARY_VERSION, meter_provider)

        # Create metrics
        meter.create_histogram(
            name=Meters.LLM_TOKEN_USAGE,
            unit="token",
            description="Measures number of input and output tokens used with Agno agents",
        )

        meter.create_histogram(
            name=Meters.LLM_OPERATION_DURATION,
            unit="s",
            description="Agno agent operation duration",
        )

        meter.create_counter(
            name=Meters.LLM_COMPLETIONS_EXCEPTIONS,
            unit="time",
            description="Number of exceptions occurred during Agno agent operations",
        )

        # Standard method wrapping using WrapConfig
        for wrap_config in WRAPPED_METHODS:
            try:
                wrap(wrap_config, tracer)
            except (AttributeError, ModuleNotFoundError):
                logger.debug(f"Could not wrap {wrap_config}")

        # Special handling for streaming methods
        # These require custom wrappers due to their streaming nature
        try:
            # Streaming agent methods
            wrap_function_wrapper(
                "agno.agent",
                "Agent.run",
                create_streaming_agent_wrapper(tracer),
            )
            wrap_function_wrapper(
                "agno.agent",
                "Agent.arun",
                create_streaming_agent_async_wrapper(tracer),
            )

            # Streaming workflow methods
            wrap_function_wrapper(
                "agno.workflow.workflow",
                "Workflow.run_workflow",
                create_streaming_workflow_wrapper(tracer),
            )
            wrap_function_wrapper(
                "agno.workflow.workflow",
                "Workflow.arun_workflow",
                create_streaming_workflow_async_wrapper(tracer),
            )

            # Streaming tool execution
            wrap_function_wrapper(
                "agno.tools.function",
                "FunctionCall.execute",
                create_streaming_tool_wrapper(tracer),
            )

            # Metrics wrapper
            wrap_function_wrapper(
                "agno.agent",
                "Agent._set_session_metrics",
                create_metrics_wrapper(tracer),
            )

            # Team methods
            wrap_function_wrapper(
                "agno.team.team",
                "Team.run",
                create_team_wrapper(tracer),
            )
            wrap_function_wrapper(
                "agno.team.team",
                "Team.arun",
                create_team_async_wrapper(tracer),
            )
            wrap_function_wrapper(
                "agno.team.team",
                "Team.print_response",
                create_team_wrapper(tracer),
            )

            # Team internal methods with special handling
            wrap_function_wrapper(
                "agno.team.team",
                "Team._run",
                create_team_internal_wrapper(tracer),
            )
            wrap_function_wrapper(
                "agno.team.team",
                "Team._arun",
                create_team_internal_async_wrapper(tracer),
            )

            logger.debug("Successfully wrapped Agno streaming methods")
        except (AttributeError, ModuleNotFoundError) as e:
            logger.debug(f"Failed to wrap Agno streaming methods: {e}")

        logger.info("Agno instrumentation installed successfully")

    def _uninstrument(self, **kwargs):
        """Remove instrumentation for Agno."""
        # Clear streaming contexts
        _streaming_context_manager.clear_all()

        # Unwrap standard methods
        for wrap_config in WRAPPED_METHODS:
            try:
                unwrap(wrap_config)
            except Exception:
                logger.debug(f"Failed to unwrap {wrap_config}")

        # Unwrap streaming methods
        try:
            from opentelemetry.instrumentation.utils import unwrap as otel_unwrap

            # Agent methods
            otel_unwrap("agno.agent", "Agent.run")
            otel_unwrap("agno.agent", "Agent.arun")

            # Workflow methods
            otel_unwrap("agno.workflow.workflow", "Workflow.run_workflow")
            otel_unwrap("agno.workflow.workflow", "Workflow.arun_workflow")

            # Tool methods
            otel_unwrap("agno.tools.function", "FunctionCall.execute")

            # Metrics methods
            otel_unwrap("agno.agent", "Agent._set_session_metrics")

            # Team methods
            otel_unwrap("agno.team.team", "Team.run")
            otel_unwrap("agno.team.team", "Team.arun")
            otel_unwrap("agno.team.team", "Team.print_response")
            otel_unwrap("agno.team.team", "Team._run")
            otel_unwrap("agno.team.team", "Team._arun")

        except (AttributeError, ModuleNotFoundError):
            logger.debug("Failed to unwrap Agno streaming methods")

        logger.info("Agno instrumentation removed successfully")
