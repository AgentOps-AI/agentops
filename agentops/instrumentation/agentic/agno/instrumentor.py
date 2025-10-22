"""Agno Agent Instrumentation for AgentOps

This module provides instrumentation for the Agno Agent library, implementing OpenTelemetry
instrumentation for agent workflows and LLM model calls.

This provides clean visibility into agent workflows and actual tool usage with proper
parent-child span relationships.
"""

from typing import List, Any, Optional, Dict
from opentelemetry import trace, context as otel_context
from opentelemetry.trace import Status, StatusCode
from opentelemetry.metrics import Meter
import threading
import json

from agentops.logging import logger
from agentops.instrumentation.common import (
    CommonInstrumentor,
    StandardMetrics,
    InstrumentorConfig,
)
from agentops.instrumentation.common.wrappers import WrapConfig

# Import attribute handlers
from agentops.instrumentation.agentic.agno.attributes import (
    get_agent_run_attributes,
    get_metrics_attributes,
    get_team_run_attributes,
    get_tool_execution_attributes,
    get_workflow_run_attributes,
    get_workflow_session_attributes,
    get_storage_read_attributes,
    get_storage_write_attributes,
)


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


# Methods to wrap for instrumentation
# Empty list - all wrapping will be done in _custom_wrap to avoid circular imports
WRAPPED_METHODS: List[WrapConfig] = []


class StreamingResultWrapper:
    """Wrapper for streaming results that maintains agent span as active throughout iteration."""

    def __init__(self, original_result, span, agent_id, agent_context, streaming_context_manager):
        self.original_result = original_result
        self.span = span
        self.agent_id = agent_id
        self.agent_context = agent_context
        self.streaming_context_manager = streaming_context_manager
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
                self.streaming_context_manager.remove_context(self.agent_id)

    def __getattr__(self, name):
        """Delegate attribute access to the original result."""
        return getattr(self.original_result, name)


class AsyncStreamingResultWrapper:
    """Wrapper for async streaming results that maintains agent span as active throughout iteration."""

    def __init__(self, original_result, span, agent_id, agent_context, streaming_context_manager):
        self.original_result = original_result
        self.span = span
        self.agent_id = agent_id
        self.agent_context = agent_context
        self.streaming_context_manager = streaming_context_manager
        self._consumed = False

    def __aiter__(self):
        """Return async iterator that keeps agent span active during iteration."""
        return self

    async def __anext__(self):
        """Async iteration that keeps agent span active."""
        context_token = otel_context.attach(self.agent_context)
        try:
            item = await self.original_result.__anext__()
            return item
        except StopAsyncIteration:
            # Clean up when iteration is complete
            if not self._consumed:
                self._consumed = True
                self.span.end()
                self.streaming_context_manager.remove_context(self.agent_id)
            raise
        finally:
            otel_context.detach(context_token)

    def __getattr__(self, name):
        """Delegate attribute access to the original result."""
        return getattr(self.original_result, name)


def create_streaming_workflow_wrapper(tracer, streaming_context_manager):
    """Create a streaming-aware wrapper for workflow run methods."""

    def wrapper(wrapped, instance, args, kwargs):
        # Get workflow ID for context storage
        workflow_id = getattr(instance, "workflow_id", None) or getattr(instance, "id", None) or id(instance)
        workflow_id = str(workflow_id)

        # Get workflow name for span naming
        workflow_name = getattr(instance, "name", None) or type(instance).__name__
        span_name = f"{workflow_name}.agno.workflow.run.workflow" if workflow_name else "agno.workflow.run.workflow"

        # Check if streaming is enabled
        is_streaming = kwargs.get("stream", getattr(instance, "stream", False))

        # For streaming, manually manage span lifecycle
        if is_streaming:
            span = tracer.start_span(span_name)

            try:
                # Set workflow attributes
                attributes = get_workflow_run_attributes(args=(instance,) + args, kwargs=kwargs)
                for key, value in attributes.items():
                    span.set_attribute(key, value)

                # Store context for streaming - capture current context with active span
                current_context = trace.set_span_in_context(span, otel_context.get_current())
                streaming_context_manager.store_context(workflow_id, current_context, span)

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
                streaming_context_manager.remove_context(workflow_id)
                raise
        else:
            # For non-streaming, use normal context manager
            with tracer.start_as_current_span(span_name) as span:
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


def create_streaming_workflow_async_wrapper(tracer, streaming_context_manager):
    """Create a streaming-aware async wrapper for workflow run methods."""

    async def wrapper(wrapped, instance, args, kwargs):
        # Get workflow ID for context storage
        workflow_id = getattr(instance, "workflow_id", None) or getattr(instance, "id", None) or id(instance)
        workflow_id = str(workflow_id)

        # Get workflow name for span naming
        workflow_name = getattr(instance, "name", None) or type(instance).__name__
        span_name = f"{workflow_name}.agno.workflow.run.workflow" if workflow_name else "agno.workflow.run.workflow"

        # Check if streaming is enabled
        is_streaming = kwargs.get("stream", getattr(instance, "stream", False))

        # For streaming, manually manage span lifecycle
        if is_streaming:
            span = tracer.start_span(span_name)

            try:
                # Set workflow attributes
                attributes = get_workflow_run_attributes(args=(instance,) + args, kwargs=kwargs)
                for key, value in attributes.items():
                    span.set_attribute(key, value)

                # Store context for streaming - capture current context with active span
                current_context = trace.set_span_in_context(span, otel_context.get_current())
                streaming_context_manager.store_context(workflow_id, current_context, span)

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
                streaming_context_manager.remove_context(workflow_id)
                raise
        else:
            # For non-streaming, use normal context manager
            with tracer.start_as_current_span(span_name) as span:
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


def create_streaming_agent_wrapper(tracer, streaming_context_manager):
    """Create a streaming-aware wrapper for agent run methods."""

    def wrapper(wrapped, instance, args, kwargs):
        # Get agent ID for context storage
        agent_id = getattr(instance, "agent_id", None) or getattr(instance, "id", None) or id(instance)
        agent_id = str(agent_id)

        # Get session ID for context mapping
        session_id = getattr(instance, "session_id", None)

        # Get agent name for span naming
        agent_name = getattr(instance, "name", None)
        span_name = f"{agent_name}.agno.agent.run.agent" if agent_name else "agno.agent.run.agent"

        # Check if streaming is enabled
        is_streaming = kwargs.get("stream", getattr(instance, "stream", False))

        # For streaming, manually manage span lifecycle
        if is_streaming:
            span = tracer.start_span(span_name)

            try:
                # Set agent attributes
                attributes = get_agent_run_attributes(args=(instance,) + args, kwargs=kwargs)
                for key, value in attributes.items():
                    span.set_attribute(key, value)

                # Store context for streaming - capture current context with active span
                current_context = trace.set_span_in_context(span, otel_context.get_current())
                streaming_context_manager.store_context(agent_id, current_context, span)

                # Store session-to-agent mapping for LLM context lookup
                if session_id:
                    streaming_context_manager.store_agent_session_mapping(session_id, agent_id)

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
                    return StreamingResultWrapper(result, span, agent_id, current_context, streaming_context_manager)
                else:
                    # Not actually streaming, clean up immediately
                    span.end()
                    streaming_context_manager.remove_context(agent_id)
                    return result

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                span.end()
                streaming_context_manager.remove_context(agent_id)
                raise
        else:
            # For non-streaming, use normal context manager
            with tracer.start_as_current_span(span_name) as span:
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


def create_streaming_agent_async_wrapper(tracer, streaming_context_manager):
    """Create a streaming-aware async wrapper for agent run methods."""

    def wrapper(wrapped, instance, args, kwargs):
        import inspect

        # Get agent ID for context storage
        agent_id = getattr(instance, "agent_id", None) or getattr(instance, "id", None) or id(instance)
        agent_id = str(agent_id)

        # Get session ID for context mapping
        session_id = getattr(instance, "session_id", None)

        # Get agent name for span naming
        agent_name = getattr(instance, "name", None)
        span_name = f"{agent_name}.agno.agent.run.agent" if agent_name else "agno.agent.run.agent"

        # Check if streaming is enabled
        is_streaming = kwargs.get("stream", getattr(instance, "stream", False))

        # For streaming, manually manage span lifecycle
        if is_streaming:
            span = tracer.start_span(span_name)

            try:
                # Set agent attributes
                attributes = get_agent_run_attributes(args=(instance,) + args, kwargs=kwargs)
                for key, value in attributes.items():
                    span.set_attribute(key, value)

                # Store context for streaming - capture current context with active span
                current_context = trace.set_span_in_context(span, otel_context.get_current())
                streaming_context_manager.store_context(agent_id, current_context, span)

                # Store session-to-agent mapping for LLM context lookup
                if session_id:
                    streaming_context_manager.store_agent_session_mapping(session_id, agent_id)

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
                if inspect.isasyncgen(result):
                    return AsyncStreamingResultWrapper(
                        result, span, agent_id, current_context, streaming_context_manager
                    )
                elif hasattr(result, "__iter__"):
                    return StreamingResultWrapper(result, span, agent_id, current_context, streaming_context_manager)
                else:
                    # Not actually streaming, clean up immediately
                    span.end()
                    streaming_context_manager.remove_context(agent_id)
                    return result

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                span.end()
                streaming_context_manager.remove_context(agent_id)
                raise
        else:
            # For non-streaming, need to handle async call
            async def async_wrapper():
                with tracer.start_as_current_span(span_name) as span:
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

            return async_wrapper()

    return wrapper


def create_streaming_tool_wrapper(tracer, streaming_context_manager):
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
                context_info = streaming_context_manager.get_context(agent_id)
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
                    context_info = streaming_context_manager.get_context(workflow_id)
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


def create_metrics_wrapper(tracer, streaming_context_manager):
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

                span.set_status(Status(StatusCode.OK))

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    return wrapper


def create_team_internal_wrapper(tracer, streaming_context_manager):
    """Create a wrapper for Team internal methods (_run/_arun) that manages team span lifecycle."""

    def wrapper(wrapped, instance, args, kwargs):
        # Get team ID for context storage
        team_id = getattr(instance, "team_id", None) or getattr(instance, "id", None) or id(instance)
        team_id = str(team_id)

        # Get team name for span naming
        team_name = getattr(instance, "name", None)
        span_name = f"{team_name}.agno.team.run.workflow" if team_name else "agno.team.run.workflow"

        # Check if we already have a team context (from print_response)
        existing_context = streaming_context_manager.get_context(team_id)

        if existing_context:
            # We're being called from print_response, use existing context
            parent_context, parent_span = existing_context

            # Execute within the existing team context
            context_token = otel_context.attach(parent_context)
            try:
                with tracer.start_as_current_span(span_name) as span:
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
                            streaming_context_manager.remove_context(team_id)
            finally:
                otel_context.detach(context_token)
        else:
            # Direct call to _run, create new team span
            with tracer.start_as_current_span(span_name) as span:
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


def create_team_internal_async_wrapper(tracer, streaming_context_manager):
    """Create an async wrapper for Team internal methods (_arun) that manages team span lifecycle."""

    async def wrapper(wrapped, instance, args, kwargs):
        # Get team ID for context storage
        team_id = getattr(instance, "team_id", None) or getattr(instance, "id", None) or id(instance)
        team_id = str(team_id)

        # Get team name for span naming
        team_name = getattr(instance, "name", None)
        span_name = f"{team_name}.agno.team.run.workflow" if team_name else "agno.team.run.workflow"

        # Check if we already have a team context (from print_response)
        existing_context = streaming_context_manager.get_context(team_id)

        if existing_context:
            # We're being called from print_response, use existing context
            parent_context, parent_span = existing_context

            # Execute within the existing team context
            context_token = otel_context.attach(parent_context)
            try:
                with tracer.start_as_current_span(span_name) as span:
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
                            streaming_context_manager.remove_context(team_id)
            finally:
                otel_context.detach(context_token)
        else:
            # Direct call to _arun, create new team span
            with tracer.start_as_current_span(span_name) as span:
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


def create_team_wrapper(tracer, streaming_context_manager):
    """Create a wrapper for Team methods that establishes the team context."""

    def wrapper(wrapped, instance, args, kwargs):
        # Get team ID for context storage
        team_id = getattr(instance, "team_id", None) or getattr(instance, "id", None) or id(instance)
        team_id = str(team_id)

        # Check if streaming is enabled
        is_streaming = kwargs.get("stream", getattr(instance, "stream", False))

        # Get team name for span naming
        team_name = getattr(instance, "name", None)
        base_span_name = f"{team_name}.agno.team.run.workflow" if team_name else "agno.team.run.workflow"

        # For print_response, we need to wrap the internal _run method instead
        # because print_response returns immediately
        if wrapped.__name__ == "print_response":
            # Create team span but don't manage it here
            span = tracer.start_span(base_span_name)

            try:
                # Set team attributes
                attributes = get_team_run_attributes(args=(instance,) + args, kwargs=kwargs)
                for key, value in attributes.items():
                    span.set_attribute(key, value)

                # Store context for child spans
                current_context = trace.set_span_in_context(span, otel_context.get_current())
                streaming_context_manager.store_context(team_id, current_context, span)

                # The span will be closed by the internal _run method
                # Just execute print_response normally
                result = wrapped(*args, **kwargs)
                return result

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                span.end()
                streaming_context_manager.remove_context(team_id)
                raise
        else:
            # For run/arun methods, use standard span management
            span = tracer.start_span(base_span_name)

            try:
                # Set team attributes
                attributes = get_team_run_attributes(args=(instance,) + args, kwargs=kwargs)
                for key, value in attributes.items():
                    span.set_attribute(key, value)

                # Store context for child spans
                current_context = trace.set_span_in_context(span, otel_context.get_current())
                streaming_context_manager.store_context(team_id, current_context, span)

                # Execute the original function within team context
                context_token = otel_context.attach(current_context)
                try:
                    result = wrapped(*args, **kwargs)

                    # For streaming results, wrap them to keep span alive
                    if is_streaming and hasattr(result, "__iter__"):
                        return StreamingResultWrapper(result, span, team_id, current_context, streaming_context_manager)
                    else:
                        # Non-streaming, close span
                        span.end()
                        streaming_context_manager.remove_context(team_id)
                        return result

                finally:
                    otel_context.detach(context_token)

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                span.end()
                streaming_context_manager.remove_context(team_id)
                raise

    return wrapper


def create_team_async_wrapper(tracer, streaming_context_manager):
    """Create an async wrapper for Team methods that establishes the team context."""

    def wrapper(wrapped, instance, args, kwargs):
        import inspect

        # Get team ID for context storage
        team_id = getattr(instance, "team_id", None) or getattr(instance, "id", None) or id(instance)
        team_id = str(team_id)

        # Check if streaming is enabled
        is_streaming = kwargs.get("stream", getattr(instance, "stream", False))

        # Get team name for span naming
        team_name = getattr(instance, "name", None)
        span_name = f"{team_name}.agno.team.run.workflow" if team_name else "agno.team.run.workflow"

        # Create team span
        span = tracer.start_span(span_name)

        try:
            # Set team attributes
            attributes = get_team_run_attributes(args=(instance,) + args, kwargs=kwargs)
            for key, value in attributes.items():
                span.set_attribute(key, value)

            # Store context for child spans - capture current context with active span
            current_context = trace.set_span_in_context(span, otel_context.get_current())
            streaming_context_manager.store_context(team_id, current_context, span)

            # Execute the original function within team context
            context_token = otel_context.attach(current_context)
            try:
                result = wrapped(*args, **kwargs)
            finally:
                otel_context.detach(context_token)

            # For streaming, wrap the result to maintain context
            if is_streaming and inspect.isasyncgen(result):
                return AsyncStreamingResultWrapper(result, span, team_id, current_context, streaming_context_manager)
            elif hasattr(result, "__iter__"):
                return StreamingResultWrapper(result, span, team_id, current_context, streaming_context_manager)
            else:
                span.end()
                streaming_context_manager.remove_context(team_id)
                return result

        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            span.end()
            streaming_context_manager.remove_context(team_id)
            raise

    return wrapper


def create_storage_read_wrapper(tracer, streaming_context_manager):
    """Create a wrapper for storage read operations with cache-aware span naming."""

    def wrapper(wrapped, instance, args, kwargs):
        # Start with a basic span name
        span_name = "agno.workflow.storage.read"

        with tracer.start_as_current_span(span_name) as span:
            try:
                # Set flag to indicate we're in a storage operation
                SessionStateProxy._set_storage_operation(True)

                # Set initial attributes
                attributes = get_storage_read_attributes(args=(instance,) + args, kwargs=kwargs)
                for key, value in attributes.items():
                    span.set_attribute(key, value)

                # Execute the original function
                result = wrapped(*args, **kwargs)

                # Set result attributes including cache hit/miss
                result_attributes = get_storage_read_attributes(
                    args=(instance,) + args, kwargs=kwargs, return_value=result
                )
                for key, value in result_attributes.items():
                    if key not in attributes:  # Avoid duplicates
                        span.set_attribute(key, value)

                # Update span name based on result and cache state
                if hasattr(instance, "session_state") and isinstance(instance.session_state, dict):
                    cache_size = len(instance.session_state)
                    if result is not None:
                        span.update_name(f"Storage.Read.Hit[cache:{cache_size}]")
                    else:
                        span.update_name(f"Storage.Read.Miss[cache:{cache_size}]")
                else:
                    # No cache info available
                    if result is not None:
                        span.update_name("Storage.Read.Hit")
                    else:
                        span.update_name("Storage.Read.Miss")

                span.set_status(Status(StatusCode.OK))
                return result

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise
            finally:
                # Clear the flag when done
                SessionStateProxy._set_storage_operation(False)

    return wrapper


def create_storage_write_wrapper(tracer, streaming_context_manager):
    """Create a wrapper for storage write operations with descriptive span naming."""

    def wrapper(wrapped, instance, args, kwargs):
        # Start with a basic span name
        span_name = "agno.workflow.storage.write"

        with tracer.start_as_current_span(span_name) as span:
            try:
                # Set flag to indicate we're in a storage operation
                SessionStateProxy._set_storage_operation(True)

                # Set initial attributes
                attributes = get_storage_write_attributes(args=(instance,) + args, kwargs=kwargs)
                for key, value in attributes.items():
                    span.set_attribute(key, value)

                # Execute the original function
                result = wrapped(*args, **kwargs)

                # Set result attributes
                result_attributes = get_storage_write_attributes(
                    args=(instance,) + args, kwargs=kwargs, return_value=result
                )
                for key, value in result_attributes.items():
                    if key not in attributes:  # Avoid duplicates
                        span.set_attribute(key, value)

                # Update span name to show cache state after write
                if hasattr(instance, "session_state") and isinstance(instance.session_state, dict):
                    cache_size = len(instance.session_state)
                    span.update_name(f"Storage.Write[cache:{cache_size}]")
                else:
                    span.update_name("Storage.Write")

                span.set_status(Status(StatusCode.OK))
                return result

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise
            finally:
                # Clear the flag when done
                SessionStateProxy._set_storage_operation(False)

    return wrapper


class SessionStateProxy(dict):
    """Proxy class for session_state that instruments cache operations."""

    # Thread-local storage to track if we're in a storage operation
    _thread_local = threading.local()

    def __init__(self, original_dict, workflow, tracer):
        super().__init__(original_dict)
        self._workflow = workflow
        self._tracer = tracer

    @classmethod
    def _in_storage_operation(cls):
        """Check if we're currently in a storage operation."""
        return getattr(cls._thread_local, "in_storage_operation", False)

    @classmethod
    def _set_storage_operation(cls, value):
        """Set whether we're in a storage operation."""
        cls._thread_local.in_storage_operation = value

    def get(self, key, default=None):
        """Instrumented get method for cache checking."""
        # Check if we're already in a storage operation to avoid nested spans
        if self._in_storage_operation():
            # We're inside a storage operation, skip instrumentation
            return super().get(key, default)

        span_name = "Cache.Check"

        with self._tracer.start_as_current_span(span_name) as span:
            # Set cache attributes
            span.set_attribute("cache.key", str(key))
            span.set_attribute("cache.size", len(self))
            span.set_attribute("cache.keys", json.dumps(list(self.keys())))

            # Get workflow info
            if hasattr(self._workflow, "workflow_id") and self._workflow.workflow_id:
                span.set_attribute("cache.workflow_id", str(self._workflow.workflow_id))
            if hasattr(self._workflow, "session_id") and self._workflow.session_id:
                span.set_attribute("cache.session_id", str(self._workflow.session_id))

            # Call the original method
            result = super().get(key, default)

            # Update span based on result
            if result is not None and result != default:
                span.set_attribute("cache.hit", True)
                span.set_attribute("cache.result", "hit")
                span.update_name(f"Cache.Hit[{len(self)} entries]")

                # Add value info
                if isinstance(result, str):
                    span.set_attribute("cache.value_size", len(result))
                    if len(result) <= 100:
                        span.set_attribute("cache.value", result)
                    else:
                        span.set_attribute("cache.value_preview", result[:100] + "...")
            else:
                span.set_attribute("cache.hit", False)
                span.set_attribute("cache.result", "miss")
                span.update_name(f"Cache.Miss[{len(self)} entries]")

            span.set_status(Status(StatusCode.OK))
            return result

    def __setitem__(self, key, value):
        """Instrumented setitem method for cache storing."""
        # Check if we're already in a storage operation to avoid nested spans
        if self._in_storage_operation():
            # We're inside a storage operation, skip instrumentation
            return super().__setitem__(key, value)

        span_name = "Cache.Store"

        with self._tracer.start_as_current_span(span_name) as span:
            # Set cache attributes
            span.set_attribute("cache.key", str(key))

            # Get workflow info
            if hasattr(self._workflow, "workflow_id") and self._workflow.workflow_id:
                span.set_attribute("cache.workflow_id", str(self._workflow.workflow_id))
            if hasattr(self._workflow, "session_id") and self._workflow.session_id:
                span.set_attribute("cache.session_id", str(self._workflow.session_id))

            # Call the original method
            super().__setitem__(key, value)

            # Set post-store attributes
            span.set_attribute("cache.size", len(self))
            span.set_attribute("cache.keys", json.dumps(list(self.keys())))

            # Add value info
            if isinstance(value, str):
                span.set_attribute("cache.value_size", len(value))
                if len(value) <= 100:
                    span.set_attribute("cache.value", value)
                else:
                    span.set_attribute("cache.value_preview", value[:100] + "...")

            span.update_name(f"Cache.Store[{len(self)} entries]")
            span.set_status(Status(StatusCode.OK))


def create_workflow_init_wrapper(tracer):
    """Wrapper to instrument workflow initialization and wrap session_state."""

    def wrapper(wrapped, instance, args, kwargs):
        # Call the original __init__
        result = wrapped(*args, **kwargs)

        # Wrap session_state if it exists
        if hasattr(instance, "session_state") and isinstance(instance.session_state, dict):
            # Replace session_state with our proxy
            original_state = instance.session_state
            instance.session_state = SessionStateProxy(original_state, instance, tracer)

        return result

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


class AgnoInstrumentor(CommonInstrumentor):
    """Agno instrumentation class."""

    def __init__(self):
        """Initialize the Agno instrumentor."""
        self._streaming_context_manager = StreamingContextManager()

        # Create instrumentor config with populated wrapped methods
        config = InstrumentorConfig(
            library_name="agentops.instrumentation.agno",
            library_version="0.1.0",
            wrapped_methods=self._get_initial_wrapped_methods(),
            metrics_enabled=True,
            dependencies=["agno >= 0.1.0"],
        )

        super().__init__(config)

    def _get_initial_wrapped_methods(self) -> List[WrapConfig]:
        """Return list of methods to be wrapped during initialization."""
        # Only return the standard wrapped methods that don't need custom wrappers
        return WRAPPED_METHODS.copy()

    def _create_metrics(self, meter: Meter) -> Dict[str, Any]:
        """Create metrics for the instrumentor.

        Returns a dictionary of metric name to metric instance.
        """
        # Create standard metrics for LLM operations
        return StandardMetrics.create_standard_metrics(meter)

    def _initialize(self, **kwargs):
        """Perform custom initialization."""
        logger.info("Agno instrumentation: Beginning immediate instrumentation")
        # Perform wrapping immediately instead of with a delay
        try:
            self._perform_wrapping()
            logger.info("Agno instrumentation: Immediate instrumentation completed successfully")
        except Exception as e:
            logger.error(f"Failed to perform immediate wrapping: {e}")

    def _custom_wrap(self, **kwargs):
        """Skip custom wrapping during initialization - it's done in _initialize."""
        pass

    def _perform_wrapping(self):
        """Actually perform the wrapping - called after imports are complete."""
        if not self._tracer:
            logger.debug("No tracer available for Agno wrapping")
            return

        from agentops.instrumentation.common.wrappers import wrap_function_wrapper, WrapConfig, wrap

        # Import Agno modules now that they should be fully loaded
        try:
            import agno.agent
            import agno.workflow.workflow
            import agno.tools.function
            import agno.team.team  # Noqa: F401
        except ImportError as e:
            logger.error(f"Failed to import Agno modules for wrapping: {e}")
            return

        # First wrap the standard workflow session methods using the standard wrapper
        session_methods = [
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
            # Note: read_from_storage and write_to_storage use custom wrappers below
        ]

        wrapped_count = 0
        for wrap_config in session_methods:
            try:
                wrap(wrap_config, self._tracer)
                wrapped_count += 1
            except Exception as e:
                logger.debug(f"Failed to wrap {wrap_config}: {e}")

        # Now wrap the streaming methods that need custom wrappers
        streaming_methods = [
            # Streaming agent methods
            ("agno.agent", "Agent.run", self._create_streaming_agent_wrapper()),
            ("agno.agent", "Agent.arun", self._create_streaming_agent_async_wrapper()),
            # Streaming workflow methods
            ("agno.workflow.workflow", "Workflow.run_workflow", self._create_streaming_workflow_wrapper()),
            ("agno.workflow.workflow", "Workflow.arun_workflow", self._create_streaming_workflow_async_wrapper()),
            # Streaming tool execution
            ("agno.tools.function", "FunctionCall.execute", self._create_streaming_tool_wrapper()),
            # Metrics wrapper
            ("agno.agent", "Agent._set_session_metrics", self._create_metrics_wrapper()),
            # Team methods - wrap all public and internal methods
            ("agno.team.team", "Team.print_response", self._create_team_wrapper()),
            ("agno.team.team", "Team.run", self._create_team_wrapper()),
            ("agno.team.team", "Team.arun", self._create_team_async_wrapper()),
            # Team internal methods with special handling
            ("agno.team.team", "Team._run", self._create_team_internal_wrapper()),
            ("agno.team.team", "Team._arun", self._create_team_internal_async_wrapper()),
            # Storage methods with custom wrappers for cache-aware naming
            ("agno.workflow.workflow", "Workflow.read_from_storage", self._create_storage_read_wrapper()),
            ("agno.workflow.workflow", "Workflow.write_to_storage", self._create_storage_write_wrapper()),
            # Workflow init wrapper to instrument session_state
            ("agno.workflow.workflow", "Workflow.__init__", self._create_workflow_init_wrapper()),
        ]

        for package, method, wrapper in streaming_methods:
            try:
                wrap_function_wrapper(package, method, wrapper)
                wrapped_count += 1
            except Exception as e:
                logger.debug(f"Failed to wrap {package}.{method}: {e}")

        if wrapped_count > 0:
            logger.info(f"Agno instrumentation: Successfully wrapped {wrapped_count} methods")
        else:
            logger.warning("Agno instrumentation: No methods were successfully wrapped")

    def _custom_unwrap(self, **kwargs):
        """Perform custom unwrapping."""
        # Clear streaming contexts
        self._streaming_context_manager.clear_all()
        logger.info("Agno instrumentation removed successfully")

    # Method wrappers converted to instance methods
    def _create_streaming_agent_wrapper(self, args=None, kwargs=None, return_value=None):
        """Wrapper function for streaming agent methods."""
        return create_streaming_agent_wrapper(self._tracer, self._streaming_context_manager)

    def _create_streaming_agent_async_wrapper(self, args=None, kwargs=None, return_value=None):
        """Wrapper function for async streaming agent methods."""
        return create_streaming_agent_async_wrapper(self._tracer, self._streaming_context_manager)

    def _create_streaming_workflow_wrapper(self, args=None, kwargs=None, return_value=None):
        """Wrapper function for streaming workflow methods."""
        return create_streaming_workflow_wrapper(self._tracer, self._streaming_context_manager)

    def _create_streaming_workflow_async_wrapper(self, args=None, kwargs=None, return_value=None):
        """Wrapper function for async streaming workflow methods."""
        return create_streaming_workflow_async_wrapper(self._tracer, self._streaming_context_manager)

    def _create_streaming_tool_wrapper(self, args=None, kwargs=None, return_value=None):
        """Wrapper function for streaming tool methods."""
        return create_streaming_tool_wrapper(self._tracer, self._streaming_context_manager)

    def _create_metrics_wrapper(self, args=None, kwargs=None, return_value=None):
        """Wrapper function for metrics methods."""
        return create_metrics_wrapper(self._tracer, self._streaming_context_manager)

    def _create_team_wrapper(self, args=None, kwargs=None, return_value=None):
        """Wrapper function for team methods."""
        return create_team_wrapper(self._tracer, self._streaming_context_manager)

    def _create_team_async_wrapper(self, args=None, kwargs=None, return_value=None):
        """Wrapper function for async team methods."""
        return create_team_async_wrapper(self._tracer, self._streaming_context_manager)

    def _create_team_internal_wrapper(self, args=None, kwargs=None, return_value=None):
        """Wrapper function for team internal methods."""
        return create_team_internal_wrapper(self._tracer, self._streaming_context_manager)

    def _create_team_internal_async_wrapper(self, args=None, kwargs=None, return_value=None):
        """Wrapper function for async team internal methods."""
        return create_team_internal_async_wrapper(self._tracer, self._streaming_context_manager)

    def _create_storage_read_wrapper(self, args=None, kwargs=None, return_value=None):
        """Wrapper function for storage read operations."""
        return create_storage_read_wrapper(self._tracer, self._streaming_context_manager)

    def _create_storage_write_wrapper(self, args=None, kwargs=None, return_value=None):
        """Wrapper function for storage write operations."""
        return create_storage_write_wrapper(self._tracer, self._streaming_context_manager)

    def _create_workflow_init_wrapper(self, args=None, kwargs=None, return_value=None):
        """Wrapper function for workflow initialization to instrument session_state."""
        return create_workflow_init_wrapper(self._tracer)
