import os
import time
import logging
from typing import Collection, Dict, List, Any
from contextlib import contextmanager

from wrapt import wrap_function_wrapper
from opentelemetry.trace import SpanKind, get_tracer, Tracer, get_current_span
from opentelemetry.trace.status import Status, StatusCode
from opentelemetry.metrics import Histogram, Meter, get_meter
from opentelemetry.instrumentation.utils import unwrap
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, TELEMETRY_SDK_NAME, DEPLOYMENT_ENVIRONMENT

from agentops.semconv import SpanAttributes, AgentOpsSpanKindValues, Meters, ToolAttributes
from agentops.semconv.agent import AgentAttributes
from agentops.semconv.message import MessageAttributes
from agentops.instrumentation.common.wrappers import WrapConfig, wrap
from agentops.instrumentation.common.attributes import AttributeMap
from agentops.instrumentation.crewai.version import __version__
from agentops.instrumentation.crewai.crewai_span_attributes import CrewAISpanAttributes, set_span_attribute

# Initialize logger
logger = logging.getLogger(__name__)

_instruments = ("crewai >= 0.70.0",)

# Global context to store tool executions by parent span ID
_tool_executions_by_agent = {}

@contextmanager
def store_tool_execution():
    """Context manager to store tool execution details for later attachment to agent spans."""
    parent_span = get_current_span()
    parent_span_id = getattr(parent_span.get_span_context(), "span_id", None)
    
    if parent_span_id:
        if parent_span_id not in _tool_executions_by_agent:
            _tool_executions_by_agent[parent_span_id] = []
        
        tool_details = {}
        
        try:
            yield tool_details
            
            if tool_details:
                _tool_executions_by_agent[parent_span_id].append(tool_details)
        finally:
            pass


def attach_tool_executions_to_agent_span(span):
    """Attach stored tool executions to the agent span."""
    span_id = getattr(span.get_span_context(), "span_id", None)
    
    if span_id and span_id in _tool_executions_by_agent:
        for idx, tool_execution in enumerate(_tool_executions_by_agent[span_id]):
            for key, value in tool_execution.items():
                if value is not None:
                    span.set_attribute(f"crewai.agent.tool_execution.{idx}.{key}", str(value))
        
        del _tool_executions_by_agent[span_id]


class CrewAIInstrumentor(BaseInstrumentor):
    def instrumentation_dependencies(self) -> Collection[str]:
        return _instruments

    def _instrument(self, **kwargs):
        application_name = kwargs.get("application_name", "default_application")
        environment = kwargs.get("environment", "default_environment")
        tracer_provider = kwargs.get("tracer_provider")
        tracer = get_tracer(__name__, __version__, tracer_provider)

        meter_provider = kwargs.get("meter_provider")
        meter = get_meter(__name__, __version__, meter_provider)

        if is_metrics_enabled():
            (
                token_histogram,
                duration_histogram,
            ) = _create_metrics(meter)
        else:
            (
                token_histogram,
                duration_histogram,
            ) = (None, None)

        # Use WrapConfig for consistent instrumentation patterns
        wrap_configs = [
            WrapConfig(
                trace_name="crewai.workflow",
                package="crewai.crew",
                class_name="Crew",
                method_name="kickoff",
                handler=self._create_crew_handler(tracer, duration_histogram, token_histogram, environment, application_name),
                span_kind=SpanKind.INTERNAL
            ),
            WrapConfig(
                trace_name="crewai.agent.execute_task",
                package="crewai.agent",
                class_name="Agent",
                method_name="execute_task",
                handler=self._create_agent_handler(tracer, duration_histogram, token_histogram, environment, application_name),
                span_kind=SpanKind.INTERNAL
            ),
            WrapConfig(
                trace_name="crewai.task.execute",
                package="crewai.task",
                class_name="Task",
                method_name="execute_sync",
                handler=self._create_task_handler(tracer, duration_histogram, token_histogram, environment, application_name),
                span_kind=SpanKind.INTERNAL
            ),
            WrapConfig(
                trace_name="crewai.llm.call",
                package="crewai.llm",
                class_name="LLM",
                method_name="call",
                handler=self._create_llm_handler(tracer, duration_histogram, token_histogram, environment, application_name),
                span_kind=SpanKind.CLIENT
            ),
        ]

        # Apply all wrap configurations
        for wrap_config in wrap_configs:
            wrap(wrap_config, tracer)

        # Wrap tool execution functions using original pattern for backward compatibility
        wrap_function_wrapper(
            "crewai.utilities.tool_utils", "execute_tool_and_check_finality", 
            wrap_tool_execution(tracer, duration_histogram, environment, application_name)
        )
        
        wrap_function_wrapper(
            "crewai.tools.tool_usage", "ToolUsage.use",
            wrap_tool_usage(tracer, environment, application_name)
        )

    def _uninstrument(self, **kwargs):
        unwrap("crewai.crew", "Crew.kickoff")
        unwrap("crewai.agent", "Agent.execute_task")
        unwrap("crewai.task", "Task.execute_sync")
        unwrap("crewai.llm", "LLM.call")
        unwrap("crewai.utilities.tool_utils", "execute_tool_and_check_finality")
        unwrap("crewai.tools.tool_usage", "ToolUsage.use")

    def _create_crew_handler(self, tracer, duration_histogram, token_histogram, environment, application_name):
        def handler(args=None, kwargs=None, return_value=None):
            attributes = dict()
            
            if args and len(args) > 0:
                instance = args[0]
                logger.debug(f"CrewAI: Starting workflow instrumentation for Crew with {len(getattr(instance, 'agents', []))} agents")
                
                # Set core span attributes
                attributes[TELEMETRY_SDK_NAME] = "agentops"
                attributes[SERVICE_NAME] = application_name
                attributes[DEPLOYMENT_ENVIRONMENT] = environment
                attributes[SpanAttributes.LLM_SYSTEM] = "crewai"
                
                # Process crew instance but skip agent processing at this point
                if hasattr(instance, 'agents') and instance.agents:
                    logger.debug(f"CrewAI: Found {len(instance.agents)} agents in crew")
                
            if return_value:
                logger.debug("CrewAI: Processing crew return value")
                if hasattr(return_value, "usage_metrics"):
                    attributes["crewai.crew.usage_metrics"] = str(getattr(return_value, "usage_metrics"))
                
                if hasattr(return_value, "tasks_output") and return_value.tasks_output:
                    attributes["crewai.crew.tasks_output"] = str(return_value.tasks_output)
                
            return attributes
        return handler

    def _create_agent_handler(self, tracer, duration_histogram, token_histogram, environment, application_name):
        def handler(args=None, kwargs=None, return_value=None):
            attributes = dict()
            
            # Set base attributes
            attributes[TELEMETRY_SDK_NAME] = "agentops"
            attributes[SERVICE_NAME] = application_name
            attributes[DEPLOYMENT_ENVIRONMENT] = environment
            attributes[SpanAttributes.LLM_SYSTEM] = "crewai"
            
            if args and len(args) > 0:
                instance = args[0]
                
                # Extract agent information
                if hasattr(instance, 'id'):
                    attributes[AgentAttributes.AGENT_ID] = str(instance.id)
                
                if hasattr(instance, 'role'):
                    attributes[AgentAttributes.AGENT_ROLE] = str(instance.role)
                
                if hasattr(instance, 'name'):
                    attributes[AgentAttributes.AGENT_NAME] = str(instance.name)
                
                # Process task if available
                if len(args) > 1 and args[1]:
                    task = args[1]
                    if hasattr(task, 'description'):
                        attributes["crewai.task.description"] = str(task.description)
                        attributes[SpanAttributes.AGENTOPS_ENTITY_INPUT] = str(task.description)
                    
                    if hasattr(task, 'expected_output'):
                        attributes["crewai.task.expected_output"] = str(task.expected_output)
            
            # Process return value (task output)
            if return_value:
                if isinstance(return_value, str):
                    attributes["crewai.agent.task_output"] = return_value
                    attributes[SpanAttributes.AGENTOPS_ENTITY_OUTPUT] = return_value
                
            return attributes
        return handler

    def _create_task_handler(self, tracer, duration_histogram, token_histogram, environment, application_name):
        def handler(args=None, kwargs=None, return_value=None):
            attributes = dict()
            
            # Set base attributes
            attributes[TELEMETRY_SDK_NAME] = "agentops"
            attributes[SERVICE_NAME] = application_name
            attributes[DEPLOYMENT_ENVIRONMENT] = environment
            attributes[SpanAttributes.LLM_SYSTEM] = "crewai"
            attributes[SpanAttributes.AGENTOPS_SPAN_KIND] = "workflow.step"
            
            if args and len(args) > 0:
                instance = args[0]
                
                # Process task attributes
                if hasattr(instance, 'description'):
                    attributes["crewai.task.description"] = str(instance.description)
                    attributes[SpanAttributes.AGENTOPS_ENTITY_INPUT] = str(instance.description)
                
                if hasattr(instance, 'expected_output'):
                    attributes["crewai.task.expected_output"] = str(instance.expected_output)
                
                if hasattr(instance, 'agent') and instance.agent:
                    agent = instance.agent
                    if hasattr(agent, 'id'):
                        attributes[AgentAttributes.FROM_AGENT] = str(agent.id)
                    if hasattr(agent, 'role'):
                        attributes["crewai.task.agent.role"] = str(agent.role)
            
            # Process return value
            if return_value:
                attributes["crewai.task.output"] = str(return_value)
                attributes[SpanAttributes.AGENTOPS_ENTITY_OUTPUT] = str(return_value)
            
            return attributes
        return handler

    def _create_llm_handler(self, tracer, duration_histogram, token_histogram, environment, application_name):
        def handler(args=None, kwargs=None, return_value=None):
            attributes = dict()
            
            # Set base attributes
            attributes[TELEMETRY_SDK_NAME] = "agentops"
            attributes[SERVICE_NAME] = application_name
            attributes[DEPLOYMENT_ENVIRONMENT] = environment
            attributes[SpanAttributes.LLM_SYSTEM] = "crewai"
            attributes[SpanAttributes.AGENTOPS_SPAN_KIND] = "llm"
            
            if args and len(args) > 0:
                instance = args[0]
                
                # Extract LLM model information
                model_name = getattr(instance, "model", None) or getattr(instance, "model_name", None) or ""
                attributes[SpanAttributes.LLM_REQUEST_MODEL] = model_name
                
                # Extract LLM parameters
                for param_name, attr_name in [
                    ("temperature", SpanAttributes.LLM_REQUEST_TEMPERATURE),
                    ("max_tokens", SpanAttributes.LLM_REQUEST_MAX_TOKENS),
                    ("top_p", SpanAttributes.LLM_REQUEST_TOP_P)
                ]:
                    if hasattr(instance, param_name) and getattr(instance, param_name) is not None:
                        attributes[attr_name] = str(getattr(instance, param_name))
                
                # Extract request content using MessageAttributes for indexed values
                if len(args) > 1:
                    prompt = args[1]
                    # Use MessageAttributes for prompt instead of SpanAttributes
                    attributes[MessageAttributes.CONTENT.format(i=0)] = str(prompt)
                    attributes[MessageAttributes.ROLE.format(i=0)] = "user"
                    # Keep the standard attributes for backward compatibility
                    attributes[SpanAttributes.LLM_REQUEST_PROMPT] = str(prompt)
                    attributes[SpanAttributes.LLM_REQUEST_CONTENT] = str(prompt)
            
            # Process response using MessageAttributes for completion
            if return_value:
                # Use MessageAttributes for completion
                attributes[MessageAttributes.CONTENT.format(i=1)] = str(return_value)
                attributes[MessageAttributes.ROLE.format(i=1)] = "assistant"
                # Keep standard attribute for backward compatibility
                attributes[SpanAttributes.LLM_RESPONSE_CONTENT] = str(return_value)
            
            return attributes
        return handler


def wrap_tool_execution(tracer, duration_histogram, environment, application_name):
    """Wrapper for tool execution functions."""
    
    def wrapper(wrapped, instance, args, kwargs):
        logger.debug("CrewAI: Starting tool execution instrumentation")
        
        tool_name = ""
        tool_description = ""
        input_str = ""
        agent_id = ""
        agent_role = ""

        # Extract tool info from args
        if len(args) >= 1 and args[0]:
            tool = args[0]
            if hasattr(tool, "name"):
                tool_name = tool.name
            if hasattr(tool, "description"):
                tool_description = tool.description
            
        # Extract input from args
        if len(args) >= 2:
            input_str = str(args[1])
            
        # Extract agent from args
        if len(args) >= 3 and args[2]:
            agent = args[2]
            if hasattr(agent, "id"):
                agent_id = str(agent.id)
            if hasattr(agent, "role"):
                agent_role = str(agent.role)
            
        with tracer.start_as_current_span(
            "crewai.tool.execution",
            kind=SpanKind.INTERNAL,
            attributes={
                SpanAttributes.LLM_SYSTEM: "crewai",
                TELEMETRY_SDK_NAME: "agentops",
                SERVICE_NAME: application_name,
                DEPLOYMENT_ENVIRONMENT: environment,
                SpanAttributes.AGENTOPS_SPAN_KIND: "tool",
                ToolAttributes.TOOL_NAME: tool_name,
                ToolAttributes.TOOL_DESCRIPTION: tool_description,
                ToolAttributes.TOOL_INPUT: input_str,
                AgentAttributes.FROM_AGENT: agent_id,
                "crewai.agent.role": agent_role,
            },
        ) as span:
            try:
                # Capture start time for duration measurement
                start_time = time.time()
                
                # Execute the wrapped function
                result = wrapped(*args, **kwargs)
                
                # Calculate duration in milliseconds
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000
                
                # Store duration in span
                span.set_attribute("crewai.tool.duration_ms", str(duration_ms))
                
                # Record duration in histogram if available
                if duration_histogram:
                    duration_histogram.record(duration_ms)
                
                # Store result in span - use MessageAttributes
                if result:
                    span.set_attribute(ToolAttributes.TOOL_OUTPUT, str(result))
                    # Add message format for tools as well
                    span.set_attribute(MessageAttributes.TOOL_CALL_RESPONSE.format(i=0), str(result))
                
                # Store tool execution details for later attachment to agent span
                with store_tool_execution() as tool_details:
                    tool_details["name"] = tool_name
                    tool_details["description"] = tool_description
                    tool_details["input"] = input_str
                    tool_details["output"] = str(result) if result else ""
                    tool_details["duration_ms"] = str(duration_ms)
                
                # Mark span as successful
                span.set_status(Status(StatusCode.OK))
                
                return result
            except Exception as e:
                # Record exception in span
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
                
        return result
        
    return wrapper


def wrap_tool_usage(tracer, environment, application_name):
    """Wrapper for ToolUsage.use method."""
    
    def wrapper(wrapped, instance, args, kwargs):
        logger.debug("CrewAI: Starting tool usage instrumentation")
        
        tool_name = ""
        tool_description = ""
        input_str = ""
        
        # Extract tool info from instance
        if hasattr(instance, "tool"):
            tool = instance.tool
            if hasattr(tool, "name"):
                tool_name = tool.name
            if hasattr(tool, "description"):
                tool_description = tool.description
        
        # Extract input from kwargs
        if "input_str" in kwargs:
            input_str = str(kwargs["input_str"])
            
        with tracer.start_as_current_span(
            "crewai.tool.usage",
            kind=SpanKind.INTERNAL,
            attributes={
                SpanAttributes.LLM_SYSTEM: "crewai",
                TELEMETRY_SDK_NAME: "agentops",
                SERVICE_NAME: application_name,
                DEPLOYMENT_ENVIRONMENT: environment,
                SpanAttributes.AGENTOPS_SPAN_KIND: "tool",
                ToolAttributes.TOOL_NAME: tool_name,
                ToolAttributes.TOOL_DESCRIPTION: tool_description,
                ToolAttributes.TOOL_INPUT: input_str,
                # Add message format for tool inputs
                MessageAttributes.TOOL_CALL_NAME.format(i=0): tool_name,
                MessageAttributes.TOOL_CALL_DESCRIPTION.format(i=0): tool_description,
                MessageAttributes.TOOL_CALL_ARGS.format(i=0): input_str,
            },
        ) as span:
            try:
                # Capture start time for duration measurement
                start_time = time.time()
                
                # Execute the wrapped function
                result = wrapped(*args, **kwargs)
                
                # Calculate duration in milliseconds
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000
                
                # Store duration in span
                span.set_attribute("crewai.tool.duration_ms", str(duration_ms))
                
                # Store result in span using both standard and message formats
                if result:
                    output = getattr(result, "output", str(result))
                    span.set_attribute(ToolAttributes.TOOL_OUTPUT, str(output))
                    span.set_attribute(MessageAttributes.TOOL_CALL_RESPONSE.format(i=0), str(output))
                
                # Mark span as successful
                span.set_status(Status(StatusCode.OK))
                
                return result
            except Exception as e:
                # Record exception in span
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
        
    return wrapper


def is_metrics_enabled() -> bool:
    """Check if metrics are enabled from the environment variable."""
    return os.environ.get("OTEL_METRICS_ENABLED", "1").lower() in ["1", "true", "yes"]


def _create_metrics(meter: Meter):
    """Create metrics for monitoring."""
    token_histogram = meter.create_histogram(
        name=Meters.LLM_TOKEN_USAGE,
        unit="token",
        description="Measures number of input and output tokens used",
    )

    duration_histogram = meter.create_histogram(
        name=Meters.LLM_OPERATION_DURATION,
        unit="s",
        description="GenAI operation duration",
    )
    
    return token_histogram, duration_histogram 