"""Wrapper functions for MCP Agent instrumentation.

This module provides wrapper functions that hook into MCP Agent's
telemetry system and various components to provide comprehensive
observability.
"""

import asyncio
import functools
import time
from typing import Any, Callable, Dict, Optional

from opentelemetry import trace
from opentelemetry.trace import SpanKind, Status, StatusCode

from agentops.logging import logger
from agentops.instrumentation.common import StandardMetrics
from agentops.instrumentation.providers.mcp_agent.config import Config
from agentops.semconv.span_attributes import SpanAttributes
from agentops.semconv.agent import AgentAttributes
from agentops.semconv.tool import ToolAttributes


# Create a unified Attributes class for convenience
class Attributes:
    """Unified attributes for MCP Agent instrumentation."""
    # Agent attributes
    AGENT_TYPE = "agent.type"
    AGENT_NAME = AgentAttributes.AGENT_NAME
    
    # Operation attributes
    OPERATION_TYPE = "operation.type"
    
    # Tool attributes
    TOOL_NAME = ToolAttributes.TOOL_NAME
    
    # Input/Output attributes
    INPUT_PROMPT = SpanAttributes.LLM_PROMPTS
    OUTPUT_COMPLETION = SpanAttributes.LLM_COMPLETIONS


def handle_telemetry_manager_traced(
    tracer: trace.Tracer,
    metrics: Optional[StandardMetrics],
    config: Config,
) -> Callable:
    """Wrapper for MCP Agent's TelemetryManager.traced decorator.
    
    This hooks into MCP Agent's existing telemetry system to add
    AgentOps-specific tracking while preserving their functionality.
    """
    def wrapper(wrapped, instance, args, kwargs):
        # Get the original decorator parameters
        name = args[0] if args else kwargs.get("name")
        kind = args[1] if len(args) > 1 else kwargs.get("kind", SpanKind.INTERNAL)
        attributes = args[2] if len(args) > 2 else kwargs.get("attributes", {})
        
        # Call the original traced method to get the decorator
        original_decorator = wrapped(*args, **kwargs)
        
        # Create our enhanced decorator
        def enhanced_decorator(func):
            # Apply the original decorator
            decorated_func = original_decorator(func)
            
            # Add our additional instrumentation
            @functools.wraps(decorated_func)
            async def async_wrapper(*func_args, **func_kwargs):
                span_name = f"agentops.mcp_agent.{name or func.__qualname__}"
                
                with tracer.start_as_current_span(
                    span_name,
                    kind=kind,
                    attributes={
                        Attributes.AGENT_TYPE: "mcp_agent",
                        Attributes.OPERATION_TYPE: "traced_function",
                        **attributes,
                    }
                ) as span:
                    try:
                        # Record metrics if available
                        if metrics:
                            metrics.request_counter.add(1, {
                                "operation": name or func.__qualname__,
                                "agent_type": "mcp_agent",
                            })
                        
                        # Execute the original decorated function
                        result = await decorated_func(*func_args, **func_kwargs)
                        
                        span.set_status(Status(StatusCode.OK))
                        return result
                        
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        if config.capture_errors:
                            logger.error(f"Error in MCP Agent traced function {name}: {e}")
                        raise
            
            @functools.wraps(decorated_func)
            def sync_wrapper(*func_args, **func_kwargs):
                span_name = f"agentops.mcp_agent.{name or func.__qualname__}"
                
                with tracer.start_as_current_span(
                    span_name,
                    kind=kind,
                    attributes={
                        Attributes.AGENT_TYPE: "mcp_agent",
                        Attributes.OPERATION_TYPE: "traced_function",
                        **attributes,
                    }
                ) as span:
                    try:
                        # Record metrics if available
                        if metrics:
                            metrics.request_counter.add(1, {
                                "operation": name or func.__qualname__,
                                "agent_type": "mcp_agent",
                            })
                        
                        # Execute the original decorated function
                        result = decorated_func(*func_args, **func_kwargs)
                        
                        span.set_status(Status(StatusCode.OK))
                        return result
                        
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        if config.capture_errors:
                            logger.error(f"Error in MCP Agent traced function {name}: {e}")
                        raise
            
            # Return the appropriate wrapper based on function type
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return enhanced_decorator
    
    return wrapper


def handle_tracer_configuration(
    tracer: trace.Tracer,
    metrics: Optional[StandardMetrics],
    config: Config,
) -> Callable:
    """Wrapper for MCP Agent's TracingConfig.configure method.
    
    This allows us to monitor when MCP Agent configures its tracing
    and potentially integrate with or override its configuration.
    """
    async def async_wrapper(wrapped, instance, args, kwargs):
        settings = args[0] if args else kwargs.get("settings")
        session_id = args[1] if len(args) > 1 else kwargs.get("session_id")
        force = args[2] if len(args) > 2 else kwargs.get("force", False)
        
        with tracer.start_as_current_span(
            "agentops.mcp_agent.tracer_config",
            kind=SpanKind.INTERNAL,
            attributes={
                Attributes.AGENT_TYPE: "mcp_agent",
                Attributes.OPERATION_TYPE: "tracer_configuration",
                "session_id": session_id or "unknown",
                "force": force,
                "otel_enabled": getattr(settings, "enabled", False) if settings else False,
            }
        ) as span:
            try:
                # Log configuration details if integration is enabled
                if config.integrate_with_existing_telemetry:
                    logger.debug(f"MCP Agent configuring tracer with session_id: {session_id}")
                    
                    # Optionally override configuration
                    if config.override_tracer_config and settings:
                        logger.info("Overriding MCP Agent tracer configuration with AgentOps settings")
                        # Modify settings as needed
                        # For example, add AgentOps exporter
                        if hasattr(settings, "exporters") and "agentops" not in settings.exporters:
                            settings.exporters.append("agentops")
                
                # Call the original configure method
                result = await wrapped(*args, **kwargs)
                
                span.set_status(Status(StatusCode.OK))
                return result
                
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                logger.error(f"Error configuring MCP Agent tracer: {e}")
                raise
    
    def sync_wrapper(wrapped, instance, args, kwargs):
        # Handle sync version if needed
        if asyncio.iscoroutinefunction(wrapped):
            # Run async version in event loop
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(async_wrapper(wrapped, instance, args, kwargs))
        else:
            # Direct sync implementation
            return wrapped(*args, **kwargs)
    
    return async_wrapper if asyncio.iscoroutinefunction(handle_tracer_configuration) else sync_wrapper


def handle_tool_call_attributes(
    tracer: trace.Tracer,
    metrics: Optional[StandardMetrics],
    config: Config,
) -> Callable:
    """Wrapper for MCP Agent tool calls."""
    
    async def async_wrapper(wrapped, instance, args, kwargs):
        tool_name = args[0] if args else kwargs.get("tool_name", "unknown")
        tool_args = args[1] if len(args) > 1 else kwargs.get("arguments", {})
        
        # Check if we should capture this tool
        if not config.should_capture_tool(tool_name):
            return await wrapped(*args, **kwargs)
        
        with tracer.start_as_current_span(
            f"agentops.mcp_agent.tool_call.{tool_name}",
            kind=SpanKind.CLIENT,
            attributes={
                Attributes.AGENT_TYPE: "mcp_agent",
                Attributes.OPERATION_TYPE: "tool_call",
                Attributes.TOOL_NAME: tool_name,
                "tool_args": str(tool_args)[:1000] if config.capture_prompts else "[hidden]",
            }
        ) as span:
            start_time = time.time()
            
            try:
                # Execute the tool call
                result = await wrapped(*args, **kwargs)
                
                # Record metrics
                if metrics:
                    duration_ms = (time.time() - start_time) * 1000
                    metrics.tool_calls_counter.add(1, {
                        "tool_name": tool_name,
                        "status": "success",
                    })
                    metrics.request_duration.record(duration_ms, {
                        "operation": "tool_call",
                        "tool_name": tool_name,
                    })
                
                # Capture result if configured
                if config.capture_completions and result:
                    span.set_attribute("tool_result", str(result)[:1000])
                
                span.set_status(Status(StatusCode.OK))
                return result
                
            except Exception as e:
                # Record error metrics
                if metrics:
                    metrics.tool_calls_counter.add(1, {
                        "tool_name": tool_name,
                        "status": "error",
                    })
                    metrics.error_counter.add(1, {
                        "operation": "tool_call",
                        "tool_name": tool_name,
                    })
                
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                
                if config.capture_errors:
                    logger.error(f"Error in MCP Agent tool call {tool_name}: {e}")
                raise
    
    def sync_wrapper(wrapped, instance, args, kwargs):
        tool_name = args[0] if args else kwargs.get("tool_name", "unknown")
        tool_args = args[1] if len(args) > 1 else kwargs.get("arguments", {})
        
        # Check if we should capture this tool
        if not config.should_capture_tool(tool_name):
            return wrapped(*args, **kwargs)
        
        with tracer.start_as_current_span(
            f"agentops.mcp_agent.tool_call.{tool_name}",
            kind=SpanKind.CLIENT,
            attributes={
                Attributes.AGENT_TYPE: "mcp_agent",
                Attributes.OPERATION_TYPE: "tool_call",
                Attributes.TOOL_NAME: tool_name,
                "tool_args": str(tool_args)[:1000] if config.capture_prompts else "[hidden]",
            }
        ) as span:
            start_time = time.time()
            
            try:
                # Execute the tool call
                result = wrapped(*args, **kwargs)
                
                # Record metrics
                if metrics:
                    duration_ms = (time.time() - start_time) * 1000
                    metrics.tool_calls_counter.add(1, {
                        "tool_name": tool_name,
                        "status": "success",
                    })
                    metrics.request_duration.record(duration_ms, {
                        "operation": "tool_call",
                        "tool_name": tool_name,
                    })
                
                # Capture result if configured
                if config.capture_completions and result:
                    span.set_attribute("tool_result", str(result)[:1000])
                
                span.set_status(Status(StatusCode.OK))
                return result
                
            except Exception as e:
                # Record error metrics
                if metrics:
                    metrics.tool_calls_counter.add(1, {
                        "tool_name": tool_name,
                        "status": "error",
                    })
                    metrics.error_counter.add(1, {
                        "operation": "tool_call",
                        "tool_name": tool_name,
                    })
                
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                
                if config.capture_errors:
                    logger.error(f"Error in MCP Agent tool call {tool_name}: {e}")
                raise
    
    # Return appropriate wrapper based on function type
    if asyncio.iscoroutinefunction(handle_tool_call_attributes):
        return async_wrapper
    return sync_wrapper


def handle_workflow_attributes(
    tracer: trace.Tracer,
    metrics: Optional[StandardMetrics],
    config: Config,
) -> Callable:
    """Wrapper for MCP Agent workflows."""
    
    async def async_wrapper(wrapped, instance, args, kwargs):
        workflow_name = getattr(instance, "__class__", type(instance)).__name__
        
        # Check if we should capture this workflow
        if not config.should_capture_workflow(workflow_name):
            return await wrapped(*args, **kwargs)
        
        with tracer.start_as_current_span(
            f"agentops.mcp_agent.workflow.{workflow_name}",
            kind=SpanKind.SERVER,
            attributes={
                Attributes.AGENT_TYPE: "mcp_agent",
                Attributes.OPERATION_TYPE: "workflow",
                "workflow_name": workflow_name,
            }
        ) as span:
            start_time = time.time()
            
            try:
                # Capture workflow input if configured
                if config.capture_prompts and args:
                    span.set_attribute("workflow_input", str(args[0])[:1000])
                
                # Execute the workflow
                result = await wrapped(*args, **kwargs)
                
                # Record metrics
                if metrics:
                    duration_ms = (time.time() - start_time) * 1000
                    metrics.workflow_duration.record(duration_ms, {
                        "workflow_name": workflow_name,
                        "status": "success",
                    })
                
                # Capture result if configured
                if config.capture_completions and result:
                    span.set_attribute("workflow_result", str(result)[:1000])
                
                span.set_status(Status(StatusCode.OK))
                return result
                
            except Exception as e:
                # Record error metrics
                if metrics:
                    metrics.error_counter.add(1, {
                        "operation": "workflow",
                        "workflow_name": workflow_name,
                    })
                
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                
                if config.capture_errors:
                    logger.error(f"Error in MCP Agent workflow {workflow_name}: {e}")
                raise
    
    def sync_wrapper(wrapped, instance, args, kwargs):
        workflow_name = getattr(instance, "__class__", type(instance)).__name__
        
        # Check if we should capture this workflow
        if not config.should_capture_workflow(workflow_name):
            return wrapped(*args, **kwargs)
        
        with tracer.start_as_current_span(
            f"agentops.mcp_agent.workflow.{workflow_name}",
            kind=SpanKind.SERVER,
            attributes={
                Attributes.AGENT_TYPE: "mcp_agent",
                Attributes.OPERATION_TYPE: "workflow",
                "workflow_name": workflow_name,
            }
        ) as span:
            start_time = time.time()
            
            try:
                # Capture workflow input if configured
                if config.capture_prompts and args:
                    span.set_attribute("workflow_input", str(args[0])[:1000])
                
                # Execute the workflow
                result = wrapped(*args, **kwargs)
                
                # Record metrics
                if metrics:
                    duration_ms = (time.time() - start_time) * 1000
                    metrics.workflow_duration.record(duration_ms, {
                        "workflow_name": workflow_name,
                        "status": "success",
                    })
                
                # Capture result if configured
                if config.capture_completions and result:
                    span.set_attribute("workflow_result", str(result)[:1000])
                
                span.set_status(Status(StatusCode.OK))
                return result
                
            except Exception as e:
                # Record error metrics
                if metrics:
                    metrics.error_counter.add(1, {
                        "operation": "workflow",
                        "workflow_name": workflow_name,
                    })
                
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                
                if config.capture_errors:
                    logger.error(f"Error in MCP Agent workflow {workflow_name}: {e}")
                raise
    
    # Return appropriate wrapper based on function type
    if asyncio.iscoroutinefunction(handle_workflow_attributes):
        return async_wrapper
    return sync_wrapper


def handle_agent_execution_attributes(
    tracer: trace.Tracer,
    metrics: Optional[StandardMetrics],
    config: Config,
) -> Callable:
    """Wrapper for MCP Agent execution."""
    
    async def async_wrapper(wrapped, instance, args, kwargs):
        agent_name = getattr(instance, "name", type(instance).__name__)
        prompt = args[0] if args else kwargs.get("prompt", "")
        
        with tracer.start_as_current_span(
            f"agentops.mcp_agent.agent_execution.{agent_name}",
            kind=SpanKind.SERVER,
            attributes={
                Attributes.AGENT_TYPE: "mcp_agent",
                Attributes.OPERATION_TYPE: "agent_execution",
                Attributes.AGENT_NAME: agent_name,
            }
        ) as span:
            start_time = time.time()
            
            try:
                # Capture prompt if configured
                if config.capture_prompts and prompt:
                    truncated_prompt = config.truncate_prompt(str(prompt))
                    span.set_attribute(Attributes.INPUT_PROMPT, truncated_prompt)
                
                # Execute the agent
                result = await wrapped(*args, **kwargs)
                
                # Record metrics
                if metrics:
                    duration_ms = (time.time() - start_time) * 1000
                    metrics.agent_executions_counter.add(1, {
                        "agent_name": agent_name,
                        "status": "success",
                    })
                    metrics.request_duration.record(duration_ms, {
                        "operation": "agent_execution",
                        "agent_name": agent_name,
                    })
                
                # Capture result if configured
                if config.capture_completions and result:
                    truncated_result = config.truncate_completion(str(result))
                    span.set_attribute(Attributes.OUTPUT_COMPLETION, truncated_result)
                
                span.set_status(Status(StatusCode.OK))
                return result
                
            except Exception as e:
                # Record error metrics
                if metrics:
                    metrics.agent_executions_counter.add(1, {
                        "agent_name": agent_name,
                        "status": "error",
                    })
                    metrics.error_counter.add(1, {
                        "operation": "agent_execution",
                        "agent_name": agent_name,
                    })
                
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                
                if config.capture_errors:
                    logger.error(f"Error in MCP Agent execution for {agent_name}: {e}")
                raise
    
    def sync_wrapper(wrapped, instance, args, kwargs):
        agent_name = getattr(instance, "name", type(instance).__name__)
        prompt = args[0] if args else kwargs.get("prompt", "")
        
        with tracer.start_as_current_span(
            f"agentops.mcp_agent.agent_execution.{agent_name}",
            kind=SpanKind.SERVER,
            attributes={
                Attributes.AGENT_TYPE: "mcp_agent",
                Attributes.OPERATION_TYPE: "agent_execution",
                Attributes.AGENT_NAME: agent_name,
            }
        ) as span:
            start_time = time.time()
            
            try:
                # Capture prompt if configured
                if config.capture_prompts and prompt:
                    truncated_prompt = config.truncate_prompt(str(prompt))
                    span.set_attribute(Attributes.INPUT_PROMPT, truncated_prompt)
                
                # Execute the agent
                result = wrapped(*args, **kwargs)
                
                # Record metrics
                if metrics:
                    duration_ms = (time.time() - start_time) * 1000
                    metrics.agent_executions_counter.add(1, {
                        "agent_name": agent_name,
                        "status": "success",
                    })
                    metrics.request_duration.record(duration_ms, {
                        "operation": "agent_execution",
                        "agent_name": agent_name,
                    })
                
                # Capture result if configured
                if config.capture_completions and result:
                    truncated_result = config.truncate_completion(str(result))
                    span.set_attribute(Attributes.OUTPUT_COMPLETION, truncated_result)
                
                span.set_status(Status(StatusCode.OK))
                return result
                
            except Exception as e:
                # Record error metrics
                if metrics:
                    metrics.agent_executions_counter.add(1, {
                        "agent_name": agent_name,
                        "status": "error",
                    })
                    metrics.error_counter.add(1, {
                        "operation": "agent_execution",
                        "agent_name": agent_name,
                    })
                
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                
                if config.capture_errors:
                    logger.error(f"Error in MCP Agent execution for {agent_name}: {e}")
                raise
    
    # Return appropriate wrapper based on function type
    if asyncio.iscoroutinefunction(handle_agent_execution_attributes):
        return async_wrapper
    return sync_wrapper