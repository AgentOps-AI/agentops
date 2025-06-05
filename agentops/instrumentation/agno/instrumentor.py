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

This provides clean visibility into agent workflows and actual tool usage with proper 
parent-child span relationships.
"""

from typing import List, Collection, Any, Optional, Dict
from opentelemetry.trace import get_tracer, SpanKind
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.metrics import get_meter
from opentelemetry.util.types import AttributeValue
from opentelemetry import trace, context as otel_context
from opentelemetry.trace import Status, StatusCode
import threading
import weakref

from agentops.logging import logger
from agentops.semconv import Meters
from agentops.semconv.span_kinds import SpanKind as AgentOpsSpanKind

# Import attribute handlers
from agentops.instrumentation.agno.attributes.agent import get_agent_run_attributes
from agentops.instrumentation.agno.attributes.team import get_team_run_attributes  
from agentops.instrumentation.agno.attributes.tool import get_tool_execution_attributes
from agentops.instrumentation.agno.attributes.metrics import get_metrics_attributes
from agentops.instrumentation.agno.attributes.workflow import (
    get_workflow_run_attributes,
    get_workflow_session_attributes,
    get_workflow_storage_attributes
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


# Global context manager instance
_streaming_context_manager = StreamingContextManager()


def create_streaming_workflow_wrapper(original_func, is_async=False):
    """Create a streaming-aware wrapper for workflow run methods."""
    
    if is_async:
        async def async_wrapper(self, *args, **kwargs):
            tracer = trace.get_tracer(__name__)
            
            # Get workflow ID for context storage
            workflow_id = getattr(self, 'workflow_id', None) or getattr(self, 'id', None) or id(self)
            workflow_id = str(workflow_id)
            
            # Check if streaming is enabled
            is_streaming = kwargs.get('stream', getattr(self, 'stream', False))
            
            with tracer.start_as_current_span("agno.workflow.run.workflow") as span:
                try:
                    # Set workflow attributes
                    attributes = get_workflow_run_attributes(args=(self,) + args, kwargs=kwargs)
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                    
                    # Store context for streaming if needed
                    if is_streaming:
                        current_context = otel_context.get_current()
                        _streaming_context_manager.store_context(workflow_id, current_context, span)
                    
                    # Execute the original function
                    result = await original_func(self, *args, **kwargs)
                    
                    # Set result attributes
                    result_attributes = get_workflow_run_attributes(args=(self,) + args, kwargs=kwargs, return_value=result)
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
                    # For non-streaming, remove context immediately
                    if not is_streaming:
                        _streaming_context_manager.remove_context(workflow_id)
        
        return async_wrapper
    else:
        def sync_wrapper(self, *args, **kwargs):
            tracer = trace.get_tracer(__name__)
            
            # Get workflow ID for context storage
            workflow_id = getattr(self, 'workflow_id', None) or getattr(self, 'id', None) or id(self)
            workflow_id = str(workflow_id)
            
            # Check if streaming is enabled
            is_streaming = kwargs.get('stream', getattr(self, 'stream', False))
            
            with tracer.start_as_current_span("agno.workflow.run.workflow") as span:
                try:
                    # Set workflow attributes
                    attributes = get_workflow_run_attributes(args=(self,) + args, kwargs=kwargs)
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                    
                    # Store context for streaming if needed
                    if is_streaming:
                        current_context = otel_context.get_current()
                        _streaming_context_manager.store_context(workflow_id, current_context, span)
                    
                    # Execute the original function
                    result = original_func(self, *args, **kwargs)
                    
                    # Set result attributes
                    result_attributes = get_workflow_run_attributes(args=(self,) + args, kwargs=kwargs, return_value=result)
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
                    # For non-streaming, remove context immediately
                    if not is_streaming:
                        _streaming_context_manager.remove_context(workflow_id)
        
        return sync_wrapper


def create_streaming_agent_wrapper(original_func, is_async=False):
    """Create a streaming-aware wrapper for agent run methods with enhanced context propagation."""
    
    if is_async:
        async def async_wrapper(self, *args, **kwargs):
            tracer = trace.get_tracer(__name__)
            
            # Get agent ID for context storage
            agent_id = getattr(self, 'agent_id', None) or getattr(self, 'id', None) or id(self)
            agent_id = str(agent_id)
            
            # Get session ID for context mapping
            session_id = getattr(self, 'session_id', None)
            
            # Check if streaming is enabled
            is_streaming = kwargs.get('stream', getattr(self, 'stream', False))
            
            # For streaming, manually manage span lifecycle
            if is_streaming:
                span = tracer.start_span("agno.agent.run.agent")
                
                try:
                    # Set agent attributes
                    attributes = get_agent_run_attributes(args=(self,) + args, kwargs=kwargs)
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
                        result = await original_func(self, *args, **kwargs)
                    finally:
                        otel_context.detach(context_token)
                    
                    # Set result attributes
                    result_attributes = get_agent_run_attributes(args=(self,) + args, kwargs=kwargs, return_value=result)
                    for key, value in result_attributes.items():
                        if key not in attributes:  # Avoid duplicates
                            span.set_attribute(key, value)
                    
                    span.set_status(Status(StatusCode.OK))
                    
                    # Wrap the result to maintain context and end span when complete
                    if hasattr(result, '__iter__'):
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
                        attributes = get_agent_run_attributes(args=(self,) + args, kwargs=kwargs)
                        for key, value in attributes.items():
                            span.set_attribute(key, value)
                        
                        # Execute the original function
                        result = await original_func(self, *args, **kwargs)
                        
                        # Set result attributes
                        result_attributes = get_agent_run_attributes(args=(self,) + args, kwargs=kwargs, return_value=result)
                        for key, value in result_attributes.items():
                            if key not in attributes:  # Avoid duplicates
                                span.set_attribute(key, value)
                        
                        span.set_status(Status(StatusCode.OK))
                        return result
                        
                    except Exception as e:
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        span.record_exception(e)
                        raise
        
        return async_wrapper
    else:
        def sync_wrapper(self, *args, **kwargs):
            tracer = trace.get_tracer(__name__)
            
            # Get agent ID for context storage
            agent_id = getattr(self, 'agent_id', None) or getattr(self, 'id', None) or id(self)
            agent_id = str(agent_id)
            
            # Get session ID for context mapping
            session_id = getattr(self, 'session_id', None)
            
            # Check if streaming is enabled
            is_streaming = kwargs.get('stream', getattr(self, 'stream', False))
            
            # For streaming, manually manage span lifecycle
            if is_streaming:
                span = tracer.start_span("agno.agent.run.agent")
                
                try:
                    # Set agent attributes
                    attributes = get_agent_run_attributes(args=(self,) + args, kwargs=kwargs)
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
                        result = original_func(self, *args, **kwargs)
                    finally:
                        otel_context.detach(context_token)
                    
                    # Set result attributes
                    result_attributes = get_agent_run_attributes(args=(self,) + args, kwargs=kwargs, return_value=result)
                    for key, value in result_attributes.items():
                        if key not in attributes:  # Avoid duplicates
                            span.set_attribute(key, value)
                    
                    span.set_status(Status(StatusCode.OK))
                    
                    # Wrap the result to maintain context and end span when complete
                    if hasattr(result, '__iter__'):
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
                        attributes = get_agent_run_attributes(args=(self,) + args, kwargs=kwargs)
                        for key, value in attributes.items():
                            span.set_attribute(key, value)
                        
                        # Execute the original function
                        result = original_func(self, *args, **kwargs)
                        
                        # Set result attributes
                        result_attributes = get_agent_run_attributes(args=(self,) + args, kwargs=kwargs, return_value=result)
                        for key, value in result_attributes.items():
                            if key not in attributes:  # Avoid duplicates
                                span.set_attribute(key, value)
                        
                        span.set_status(Status(StatusCode.OK))
                        return result
                        
                    except Exception as e:
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        span.record_exception(e)
                        raise
        
        return sync_wrapper


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


def create_streaming_tool_wrapper(original_func):
    """Create a streaming-aware wrapper for tool execution methods."""
    
    def wrapper(self, *args, **kwargs):
        tracer = trace.get_tracer(__name__)
        
        # Try to find the agent or workflow context for proper span hierarchy
        parent_context = None
        parent_span = None
        
        # Try to get context from agent
        try:
            if hasattr(self, '_agent'):
                agent = self._agent
                agent_id = getattr(agent, 'agent_id', None) or getattr(agent, 'id', None) or id(agent)
                agent_id = str(agent_id)
                context_info = _streaming_context_manager.get_context(agent_id)
                if context_info:
                    parent_context, parent_span = context_info
        except Exception:
            pass  # Continue without agent context if not found
        
        # Try to get context from workflow if agent context not found
        if not parent_context:
            try:
                if hasattr(self, '_workflow'):
                    workflow = self._workflow
                    workflow_id = getattr(workflow, 'workflow_id', None) or getattr(workflow, 'id', None) or id(workflow)
                    workflow_id = str(workflow_id)
                    context_info = _streaming_context_manager.get_context(workflow_id)
                    if context_info:
                        parent_context, parent_span = context_info
            except Exception:
                pass  # Continue without workflow context if not found
        
        # Use parent context if available, otherwise use current context
        if parent_context:
            with otel_context.use_context(parent_context):
                with tracer.start_as_current_span("agno.tool.execute.tool_usage") as span:
                    try:
                        # Set tool attributes
                        attributes = get_tool_execution_attributes(args=(self,) + args, kwargs=kwargs)
                        for key, value in attributes.items():
                            span.set_attribute(key, value)
                        
                        # Execute the original function
                        result = original_func(self, *args, **kwargs)
                        
                        # Set result attributes
                        result_attributes = get_tool_execution_attributes(args=(self,) + args, kwargs=kwargs, return_value=result)
                        for key, value in result_attributes.items():
                            if key not in attributes:  # Avoid duplicates
                                span.set_attribute(key, value)
                        
                        span.set_status(Status(StatusCode.OK))
                        return result
                        
                    except Exception as e:
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        span.record_exception(e)
                        raise
        else:
            # Fallback to normal span creation
            with tracer.start_as_current_span("agno.tool.execute.tool_usage") as span:
                try:
                    # Set tool attributes
                    attributes = get_tool_execution_attributes(args=(self,) + args, kwargs=kwargs)
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                    
                    # Execute the original function
                    result = original_func(self, *args, **kwargs)
                    
                    # Set result attributes
                    result_attributes = get_tool_execution_attributes(args=(self,) + args, kwargs=kwargs, return_value=result)
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


def get_agent_context_for_llm():
    """Helper function for LLM instrumentation to get current agent context."""
    current_context = otel_context.get_current()
    current_span = trace.get_current_span(current_context)
    
    # Check if we're already in an agent span
    if current_span and hasattr(current_span, 'name') and 'agent' in current_span.name:
        return current_context, current_span
    
    # Try to find stored agent context by checking active contexts
    # This is a fallback for cases where context isn't properly propagated
    return None, None


class AgnoInstrumentor(BaseInstrumentor):
    """Agno instrumentation class."""

    _original_methods = {}  # Store original methods for cleanup

    def instrumentation_dependencies(self) -> Collection[str]:
        """Returns list of packages required for instrumentation."""
        return []
        
    def _instrument(self, **kwargs):
        """Install instrumentation for Agno."""
        tracer = get_tracer(__name__)
        
        try:
            # Apply workflow instrumentation
            try:
                import agno.workflow.workflow
                if hasattr(agno.workflow.workflow, 'Workflow'):
                    # Store original methods for cleanup
                    self._original_methods['Workflow.run_workflow'] = getattr(agno.workflow.workflow.Workflow, 'run_workflow', None)
                    self._original_methods['Workflow.arun_workflow'] = getattr(agno.workflow.workflow.Workflow, 'arun_workflow', None)
                    
                    # Wrap main workflow execution methods
                    if self._original_methods['Workflow.run_workflow']:
                        agno.workflow.workflow.Workflow.run_workflow = create_streaming_workflow_wrapper(
                            agno.workflow.workflow.Workflow.run_workflow, is_async=False
                        )
                    if self._original_methods['Workflow.arun_workflow']:
                        agno.workflow.workflow.Workflow.arun_workflow = create_streaming_workflow_wrapper(
                            agno.workflow.workflow.Workflow.arun_workflow, is_async=True
                        )
                    
                    # Wrap session management methods
                    session_methods = ['load_session', 'new_session', 'read_from_storage', 'write_to_storage']
                    for method_name in session_methods:
                        original_method = getattr(agno.workflow.workflow.Workflow, method_name, None)
                        if original_method:
                            self._original_methods[f'Workflow.{method_name}'] = original_method
                            setattr(agno.workflow.workflow.Workflow, method_name, 
                                   self._create_session_wrapper(original_method, method_name))
                    
                    logger.debug("Successfully wrapped Workflow methods with streaming context support")
            except ImportError:
                logger.debug("Workflow module not found, skipping workflow instrumentation")
            
            # Apply streaming-aware agent wrappers
            import agno.agent
            if hasattr(agno.agent, 'Agent'):
                # Store original methods for cleanup
                self._original_methods['Agent.run'] = agno.agent.Agent.run
                self._original_methods['Agent.arun'] = agno.agent.Agent.arun
                
                agno.agent.Agent.run = create_streaming_agent_wrapper(agno.agent.Agent.run, is_async=False)
                agno.agent.Agent.arun = create_streaming_agent_wrapper(agno.agent.Agent.arun, is_async=True)
                
                logger.debug("Successfully wrapped Agent.run and Agent.arun with enhanced streaming context support")
            
            # Apply streaming-aware tool wrappers
            import agno.tools.function
            if hasattr(agno.tools.function, 'FunctionCall'):
                # Store original method for cleanup
                self._original_methods['FunctionCall.execute'] = agno.tools.function.FunctionCall.execute
                
                agno.tools.function.FunctionCall.execute = create_streaming_tool_wrapper(agno.tools.function.FunctionCall.execute)
                
                logger.debug("Successfully wrapped FunctionCall.execute with streaming context support")
            
            # Apply standard team and metrics wrappers if needed
            try:
                import agno.team.team
                if hasattr(agno.team.team, 'Team'):
                    self._original_methods['Team._run'] = getattr(agno.team.team.Team, '_run', None)
                    self._original_methods['Team._arun'] = getattr(agno.team.team.Team, '_arun', None)
                    
                    if self._original_methods['Team._run']:
                        agno.team.team.Team._run = self._create_standard_wrapper(
                            agno.team.team.Team._run, "agno.team.run.workflow", get_team_run_attributes, is_async=False
                        )
                    if self._original_methods['Team._arun']:
                        agno.team.team.Team._arun = self._create_standard_wrapper(
                            agno.team.team.Team._arun, "agno.team.run.workflow", get_team_run_attributes, is_async=True
                        )
                    
                    logger.debug("Successfully wrapped Team._run and Team._arun")
            except ImportError:
                logger.debug("Team module not found, skipping team instrumentation")
            
            # Apply metrics wrapper
            try:
                if hasattr(agno.agent.Agent, '_set_session_metrics'):
                    self._original_methods['Agent._set_session_metrics'] = agno.agent.Agent._set_session_metrics
                    agno.agent.Agent._set_session_metrics = self._create_llm_metrics_wrapper(
                        agno.agent.Agent._set_session_metrics, get_metrics_attributes
                    )
                    logger.debug("Successfully wrapped Agent._set_session_metrics")
            except AttributeError:
                logger.debug("_set_session_metrics method not found, skipping metrics instrumentation")
            
            logger.info("Agno instrumentation installed successfully with enhanced workflow and streaming context support")
            
        except Exception as e:
            logger.error(f"Failed to install Agno instrumentation: {e}")
            raise

    def _create_session_wrapper(self, original_func, method_name):
        """Create a wrapper for workflow session management methods."""
        
        def wrapper(self, *args, **kwargs):
            tracer = trace.get_tracer(__name__)
            span_name = f"agno.workflow.session.{method_name}"
            
            with tracer.start_as_current_span(span_name) as span:
                try:
                    # Set session attributes
                    attributes = get_workflow_session_attributes(args=(self,) + args, kwargs=kwargs)
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                    
                    # Execute the original function
                    result = original_func(self, *args, **kwargs)
                    
                    # Set result attributes
                    result_attributes = get_workflow_session_attributes(args=(self,) + args, kwargs=kwargs, return_value=result)
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

    def _create_standard_wrapper(self, original_func, span_name, attributes_handler, is_async=False):
        """Create a standard wrapper for non-streaming methods."""
        
        if is_async:
            async def async_wrapper(self, *args, **kwargs):
                tracer = trace.get_tracer(__name__)
                with tracer.start_as_current_span(span_name) as span:
                    try:
                        # Set attributes
                        attributes = attributes_handler(args=(self,) + args, kwargs=kwargs)
                        for key, value in attributes.items():
                            span.set_attribute(key, value)
                        
                        # Execute the original function
                        result = await original_func(self, *args, **kwargs)
                        
                        # Set result attributes
                        result_attributes = attributes_handler(args=(self,) + args, kwargs=kwargs, return_value=result)
                        for key, value in result_attributes.items():
                            if key not in attributes:  # Avoid duplicates
                                span.set_attribute(key, value)
                        
                        span.set_status(Status(StatusCode.OK))
                        return result
                        
                    except Exception as e:
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        span.record_exception(e)
                        raise
            
            return async_wrapper
        else:
            def sync_wrapper(self, *args, **kwargs):
                tracer = trace.get_tracer(__name__)
                with tracer.start_as_current_span(span_name) as span:
                    try:
                        # Set attributes
                        attributes = attributes_handler(args=(self,) + args, kwargs=kwargs)
                        for key, value in attributes.items():
                            span.set_attribute(key, value)
                        
                        # Execute the original function
                        result = original_func(self, *args, **kwargs)
                        
                        # Set result attributes
                        result_attributes = attributes_handler(args=(self,) + args, kwargs=kwargs, return_value=result)
                        for key, value in result_attributes.items():
                            if key not in attributes:  # Avoid duplicates
                                span.set_attribute(key, value)
                        
                        span.set_status(Status(StatusCode.OK))
                        return result
                        
                    except Exception as e:
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        span.record_exception(e)
                        raise
            
            return sync_wrapper

    def _create_llm_metrics_wrapper(self, original_func, attributes_handler):
        """Create an LLM metrics wrapper with dynamic span naming."""
        
        def wrapper(self, *args, **kwargs):
            tracer = trace.get_tracer(__name__)
            
            # Extract model ID for dynamic span naming
            span_name = "agno.agent.metrics"  # fallback
            if hasattr(self, 'model') and self.model and hasattr(self.model, 'id'):
                model_id = str(self.model.id)
                span_name = f"{model_id}.llm"
            
            with tracer.start_as_current_span(span_name) as span:
                try:
                    # Set attributes
                    attributes = attributes_handler(args=(self,) + args, kwargs=kwargs)
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                    
                    # Execute the original function
                    result = original_func(self, *args, **kwargs)
                    
                    # Set result attributes
                    result_attributes = attributes_handler(args=(self,) + args, kwargs=kwargs, return_value=result)
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

    def _uninstrument(self, **kwargs):
        """Remove instrumentation for Agno."""
        try:
            # Clear streaming contexts
            _streaming_context_manager.clear_all()
            
            # Restore original workflow methods
            if 'Workflow.run_workflow' in self._original_methods and self._original_methods['Workflow.run_workflow']:
                import agno.workflow.workflow
                agno.workflow.workflow.Workflow.run_workflow = self._original_methods['Workflow.run_workflow']
                agno.workflow.workflow.Workflow.arun_workflow = self._original_methods['Workflow.arun_workflow']
                logger.debug("Restored original Workflow.run_workflow and Workflow.arun_workflow methods")
            
            # Restore workflow session methods
            workflow_session_methods = ['load_session', 'new_session', 'read_from_storage', 'write_to_storage']
            for method_name in workflow_session_methods:
                key = f'Workflow.{method_name}'
                if key in self._original_methods and self._original_methods[key]:
                    import agno.workflow.workflow
                    setattr(agno.workflow.workflow.Workflow, method_name, self._original_methods[key])
                    logger.debug(f"Restored original Workflow.{method_name} method")
            
            # Restore original agent methods
            if 'Agent.run' in self._original_methods:
                import agno.agent
                agno.agent.Agent.run = self._original_methods['Agent.run']
                agno.agent.Agent.arun = self._original_methods['Agent.arun']
                logger.debug("Restored original Agent.run and Agent.arun methods")
            
            # Restore original tool methods
            if 'FunctionCall.execute' in self._original_methods:
                import agno.tools.function
                agno.tools.function.FunctionCall.execute = self._original_methods['FunctionCall.execute']
                logger.debug("Restored original FunctionCall.execute method")
            
            # Restore team methods
            if 'Team._run' in self._original_methods and self._original_methods['Team._run']:
                import agno.team.team
                agno.team.team.Team._run = self._original_methods['Team._run']
                agno.team.team.Team._arun = self._original_methods['Team._arun']
                logger.debug("Restored original Team methods")
            
            # Restore metrics methods
            if 'Agent._set_session_metrics' in self._original_methods:
                import agno.agent
                agno.agent.Agent._set_session_metrics = self._original_methods['Agent._set_session_metrics']
                logger.debug("Restored original Agent._set_session_metrics method")
            
            # Clear stored original methods
            self._original_methods.clear()
            
            logger.info("Agno instrumentation removed successfully")
            
        except Exception as e:
            logger.error(f"Failed to remove Agno instrumentation: {e}")
            raise 