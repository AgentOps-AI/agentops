"""CrewAI Instrumentation for AgentOps

This module provides instrumentation for CrewAI, implementing OpenTelemetry
instrumentation for crew execution, agent interactions, and task management.

The instrumentation captures:
1. Crew execution workflow
2. Agent interactions and LLM calls
3. Task execution and results
4. Tool usage within tasks
5. Token usage metrics
"""

from typing import Collection
from opentelemetry import trace, metrics
from opentelemetry.trace import Status, StatusCode
from wrapt import wrap_function_wrapper

from agentops.instrumentation.common import AgentOpsBaseInstrumentor
from agentops.logging import logger
from agentops.instrumentation.frameworks.crewai.version import __version__
from agentops.semconv import SpanAttributes, AgentOpsSpanKindValues, Meters, ToolAttributes
from agentops.semconv.core import CoreAttributes
from agentops.instrumentation.frameworks.crewai.span_attributes import CrewAISpanAttributes, set_span_attribute

_instruments = ("crewai >= 0.1.0",)


class CrewAIInstrumentor(AgentOpsBaseInstrumentor):
    """Instrumentor for CrewAI operations."""

    def __init__(self):
        super().__init__()

    def instrumentation_dependencies(self) -> Collection[str]:
        return _instruments

    def get_library_name(self) -> str:
        return "agentops.instrumentation.frameworks.crewai"

    def get_library_version(self) -> str:
        return __version__

    def _instrument(self, **kwargs):
        """Instrument CrewAI components."""
        # Get the base tracer and meter
        super()._instrument(**kwargs)

        if not self._tracer or not self._meter:
            logger.error("Failed to initialize tracer or meter")
            return

        # Wrap CrewAI methods
        wrap_function_wrapper("crewai.crew", "Crew.kickoff", crew_kickoff_wrapper(self._tracer))
        wrap_function_wrapper("crewai.crew", "Crew.kickoff_async", crew_kickoff_async_wrapper(self._tracer))
        wrap_function_wrapper("crewai.crew", "Crew.kickoff_for_each", crew_kickoff_for_each_wrapper(self._tracer))
        wrap_function_wrapper(
            "crewai.crew", "Crew.kickoff_for_each_async", crew_kickoff_for_each_async_wrapper(self._tracer)
        )
        wrap_function_wrapper("crewai.agent", "Agent.execute", agent_execute_wrapper(self._tracer))
        wrap_function_wrapper("crewai.task", "Task.execute", task_execute_wrapper(self._tracer, self._meter))
        wrap_function_wrapper("crewai.task", "Task.execute_sync", task_execute_sync_wrapper(self._tracer, self._meter))
        wrap_function_wrapper(
            "crewai.task", "Task.execute_async", task_execute_async_wrapper(self._tracer, self._meter)
        )
        wrap_function_wrapper("crewai.tools.base_tool", "BaseTool._run", tool_wrapper(self._tracer, self._meter))
        wrap_function_wrapper("crewai.tools.base_tool", "BaseTool._arun", tool_async_wrapper(self._tracer, self._meter))
        wrap_function_wrapper("crewai.tools", "BaseTool.run", tool_run_wrapper(self._tracer, self._meter))
        wrap_function_wrapper("crewai.tools", "tool_calling", tool_calling_wrapper(self._tracer))
        wrap_function_wrapper("crewai.agent", "Agent._execute", agent_execute_internal_wrapper(self._tracer))

    def _uninstrument(self, **kwargs):
        """Remove instrumentation from CrewAI."""
        from opentelemetry.instrumentation.utils import unwrap

        unwrap("crewai.crew", "Crew.kickoff")
        unwrap("crewai.crew", "Crew.kickoff_async")
        unwrap("crewai.crew", "Crew.kickoff_for_each")
        unwrap("crewai.crew", "Crew.kickoff_for_each_async")
        unwrap("crewai.agent", "Agent.execute")
        unwrap("crewai.task", "Task.execute")
        unwrap("crewai.task", "Task.execute_sync")
        unwrap("crewai.task", "Task.execute_async")
        unwrap("crewai.tools.base_tool", "BaseTool._run")
        unwrap("crewai.tools.base_tool", "BaseTool._arun")
        unwrap("crewai.tools", "BaseTool.run")
        unwrap("crewai.tools", "tool_calling")
        unwrap("crewai.agent", "Agent._execute")


# Wrapper functions remain the same but are defined outside the class
def crew_kickoff_wrapper(tracer):
    """Wrapper for Crew.kickoff method."""

    def wrapper(wrapped, instance, args, kwargs):
        from agentops import get_client

        application_name = kwargs.get("application_name", "default_application")
        attributes = {
            SpanAttributes.LLM_SYSTEM: "crewai",
        }

        # Add default tags from config
        config = get_client().config
        if config.default_tags:
            tag_list = list(config.default_tags)
            attributes[CoreAttributes.TAGS] = tag_list

        with tracer.start_as_current_span(
            f"{application_name}.crew.kickoff",
            kind=trace.SpanKind.CLIENT,
            attributes=attributes,
        ) as span:
            try:
                crewai_span_attributes = CrewAISpanAttributes(span)
                crewai_span_attributes.set_crew_attributes(instance, args, kwargs)

                result = wrapped(*args, **kwargs)

                if result:
                    crewai_span_attributes.set_crew_output_attributes(result)

                span.set_status(Status(StatusCode.OK))
                return result
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    return wrapper


def crew_kickoff_async_wrapper(tracer):
    """Wrapper for async Crew.kickoff_async method."""

    async def wrapper(wrapped, instance, args, kwargs):
        from agentops import get_client

        application_name = kwargs.get("application_name", "default_application")
        attributes = {
            SpanAttributes.LLM_SYSTEM: "crewai",
        }

        # Add default tags from config
        config = get_client().config
        if config.default_tags:
            tag_list = list(config.default_tags)
            attributes[CoreAttributes.TAGS] = tag_list

        with tracer.start_as_current_span(
            f"{application_name}.crew.kickoff_async",
            kind=trace.SpanKind.CLIENT,
            attributes=attributes,
        ) as span:
            try:
                crewai_span_attributes = CrewAISpanAttributes(span)
                crewai_span_attributes.set_crew_attributes(instance, args, kwargs)

                result = await wrapped(*args, **kwargs)

                if result:
                    crewai_span_attributes.set_crew_output_attributes(result)

                span.set_status(Status(StatusCode.OK))
                return result
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    return wrapper


def crew_kickoff_for_each_wrapper(tracer):
    """Wrapper for Crew.kickoff_for_each method."""

    def wrapper(wrapped, instance, args, kwargs):
        from agentops import get_client

        application_name = kwargs.get("application_name", "default_application")
        attributes = {
            SpanAttributes.LLM_SYSTEM: "crewai",
        }

        # Add default tags from config
        config = get_client().config
        if config.default_tags:
            tag_list = list(config.default_tags)
            attributes[CoreAttributes.TAGS] = tag_list

        with tracer.start_as_current_span(
            f"{application_name}.crew.kickoff_for_each",
            kind=trace.SpanKind.CLIENT,
            attributes=attributes,
        ) as span:
            try:
                crewai_span_attributes = CrewAISpanAttributes(span)
                crewai_span_attributes.set_crew_attributes(instance, args, kwargs)

                result = wrapped(*args, **kwargs)

                span.set_status(Status(StatusCode.OK))
                return result
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    return wrapper


def crew_kickoff_for_each_async_wrapper(tracer):
    """Wrapper for async Crew.kickoff_for_each_async method."""

    async def wrapper(wrapped, instance, args, kwargs):
        from agentops import get_client

        application_name = kwargs.get("application_name", "default_application")
        attributes = {
            SpanAttributes.LLM_SYSTEM: "crewai",
        }

        # Add default tags from config
        config = get_client().config
        if config.default_tags:
            tag_list = list(config.default_tags)
            attributes[CoreAttributes.TAGS] = tag_list

        with tracer.start_as_current_span(
            f"{application_name}.crew.kickoff_for_each_async",
            kind=trace.SpanKind.CLIENT,
            attributes=attributes,
        ) as span:
            try:
                crewai_span_attributes = CrewAISpanAttributes(span)
                crewai_span_attributes.set_crew_attributes(instance, args, kwargs)

                result = await wrapped(*args, **kwargs)

                span.set_status(Status(StatusCode.OK))
                return result
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    return wrapper


def agent_execute_wrapper(tracer):
    """Wrapper for Agent.execute method."""

    def wrapper(wrapped, instance, args, kwargs):
        agent_name = getattr(instance, "name", "unnamed_agent")
        span_name = f"{agent_name}.execute"

        with tracer.start_as_current_span(
            span_name,
            kind=trace.SpanKind.CLIENT,
            attributes={
                SpanAttributes.AGENTOPS_SPAN_KIND: AgentOpsSpanKindValues.AGENT.value,
            },
        ) as span:
            try:
                crewai_span_attributes = CrewAISpanAttributes(span)
                crewai_span_attributes.set_agent_attributes(instance, args, kwargs)

                # Create metrics for token usage
                if hasattr(instance, "llm") and hasattr(instance.llm, "model"):
                    meter = metrics.get_meter("agentops.instrumentation.frameworks.crewai", __version__)
                    tokens_counter = meter.create_counter(
                        name=Meters.LLM_TOKEN_USAGE,
                        unit="token",
                        description="Number of tokens used by agent",
                    )
                    tokens_counter.add(
                        0,  # Will be updated later if we get token usage
                        attributes={
                            SpanAttributes.LLM_SYSTEM: "crewai",
                            SpanAttributes.LLM_TOKEN_TYPE: "input",
                            SpanAttributes.LLM_RESPONSE_MODEL: str(instance.llm.model),
                        },
                    )
                    tokens_counter.add(
                        0,  # Will be updated later if we get token usage
                        attributes={
                            SpanAttributes.LLM_SYSTEM: "crewai",
                            SpanAttributes.LLM_TOKEN_TYPE: "output",
                            SpanAttributes.LLM_RESPONSE_MODEL: str(instance.llm.model),
                        },
                    )

                if hasattr(instance, "llm") and hasattr(instance.llm, "model"):
                    set_span_attribute(span, SpanAttributes.LLM_REQUEST_MODEL, str(instance.llm.model))
                    set_span_attribute(span, SpanAttributes.LLM_RESPONSE_MODEL, str(instance.llm.model))

                result = wrapped(*args, **kwargs)

                span.set_status(Status(StatusCode.OK))
                return result
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    return wrapper


def task_execute_wrapper(tracer, meter):
    """Wrapper for Task.execute method."""

    def wrapper(wrapped, instance, args, kwargs):
        task_description = getattr(instance, "description", "unnamed_task")[:50]
        span_name = f"task.execute: {task_description}"

        attributes = {
            SpanAttributes.AGENTOPS_SPAN_KIND: AgentOpsSpanKindValues.TASK.value,
        }

        # Add default tags from config
        from agentops import get_client

        config = get_client().config
        if config.default_tags:
            tag_list = list(config.default_tags) if hasattr(config.default_tags, "__iter__") else [config.default_tags]
            attributes[CoreAttributes.TAGS] = tag_list

        with tracer.start_as_current_span(
            span_name,
            kind=trace.SpanKind.CLIENT,
            attributes=attributes,
        ) as span:
            try:
                crewai_span_attributes = CrewAISpanAttributes(span)
                crewai_span_attributes.set_task_attributes(instance, args, kwargs)

                result = wrapped(*args, **kwargs)

                set_span_attribute(span, SpanAttributes.AGENTOPS_ENTITY_OUTPUT, str(result))
                span.set_status(Status(StatusCode.OK))
                return result
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    return wrapper


def task_execute_sync_wrapper(tracer, meter):
    """Wrapper for Task.execute_sync method."""
    return task_execute_wrapper(tracer, meter)  # Same logic for sync


def task_execute_async_wrapper(tracer, meter):
    """Wrapper for async Task.execute_async method."""

    async def wrapper(wrapped, instance, args, kwargs):
        task_description = getattr(instance, "description", "unnamed_task")[:50]
        span_name = f"task.execute_async: {task_description}"

        attributes = {
            SpanAttributes.AGENTOPS_SPAN_KIND: AgentOpsSpanKindValues.TASK.value,
        }

        # Add default tags from config
        from agentops import get_client

        config = get_client().config
        if config.default_tags:
            tag_list = list(config.default_tags) if hasattr(config.default_tags, "__iter__") else [config.default_tags]
            attributes[CoreAttributes.TAGS] = tag_list

        with tracer.start_as_current_span(
            span_name,
            kind=trace.SpanKind.CLIENT,
            attributes=attributes,
        ) as span:
            try:
                crewai_span_attributes = CrewAISpanAttributes(span)
                crewai_span_attributes.set_task_attributes(instance, args, kwargs)

                result = await wrapped(*args, **kwargs)

                set_span_attribute(span, SpanAttributes.AGENTOPS_ENTITY_OUTPUT, str(result))
                span.set_status(Status(StatusCode.OK))
                return result
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    return wrapper


def agent_execute_internal_wrapper(tracer):
    """Wrapper for Agent._execute internal method."""

    def wrapper(wrapped, instance, args, kwargs):
        result = wrapped(*args, **kwargs)

        # Check if instance has token_process attribute (from LiteLLM)
        if hasattr(instance, "token_process"):
            token_process = instance.token_process
            current_span = trace.get_current_span()

            if current_span and current_span.is_recording():
                if hasattr(token_process, "model") and hasattr(token_process, "llm") and token_process.llm:
                    # Set model information
                    current_span.set_attribute(SpanAttributes.LLM_REQUEST_MODEL, str(token_process.model))
                    current_span.set_attribute(SpanAttributes.LLM_RESPONSE_MODEL, str(token_process.model))

                # Set token usage if available
                if hasattr(token_process, "completion_tokens"):
                    current_span.set_attribute(
                        SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, token_process.completion_tokens
                    )
                if hasattr(token_process, "prompt_tokens"):
                    current_span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, token_process.prompt_tokens)
                if hasattr(token_process, "total_tokens"):
                    current_span.set_attribute(SpanAttributes.LLM_USAGE_TOTAL_TOKENS, token_process.total_tokens)

                # Create metrics
                meter = metrics.get_meter("agentops.instrumentation.frameworks.crewai", __version__)
                tokens_counter = meter.create_counter(
                    name=Meters.LLM_TOKEN_USAGE,
                    unit="token",
                    description="Number of tokens used",
                    attributes={
                        SpanAttributes.LLM_SYSTEM: "crewai",
                        SpanAttributes.LLM_RESPONSE_MODEL: str(instance.model),
                    },
                )

                if hasattr(token_process, "total_tokens"):
                    tokens_counter.add(token_process.total_tokens)

        return result

    return wrapper


def tool_wrapper(tracer, meter):
    """Wrapper for tool execution."""

    def wrapper(wrapped, instance, args, kwargs):
        tool_name = getattr(instance, "name", "unnamed_tool")
        span_name = f"tool.run: {tool_name}"

        tool_input = args[0] if args else kwargs.get("input", "")

        with tracer.start_as_current_span(
            span_name,
            kind=trace.SpanKind.CLIENT,
            attributes={
                SpanAttributes.AGENTOPS_SPAN_KIND: "tool",
                ToolAttributes.TOOL_NAME: tool_name,
                ToolAttributes.TOOL_PARAMETERS: str(tool_input),
            },
        ) as span:
            try:
                # Get the enclosing agent if available
                agent = getattr(instance, "_agent", None)
                if agent:
                    agent_name = getattr(agent, "name", "unnamed_agent")
                    set_span_attribute(span, "tool.agent", agent_name)

                # Set tool description if available
                if hasattr(instance, "description"):
                    span.set_attribute(ToolAttributes.TOOL_DESCRIPTION, str(instance.description))

                # Create metric for tool usage
                tool_usage_counter = meter.create_counter(
                    name="tool.usage.count",
                    unit="1",
                    description="Number of times a tool is used",
                    attributes={
                        SpanAttributes.LLM_SYSTEM: "crewai",
                        ToolAttributes.TOOL_NAME: tool_name,
                    },
                )
                tool_usage_counter.add(1)

                result = wrapped(*args, **kwargs)

                span.set_attribute(ToolAttributes.TOOL_RESULT, str(result))
                span.set_attribute(ToolAttributes.TOOL_STATUS, "success")
                span.set_status(Status(StatusCode.OK))

                return result
            except Exception as e:
                span.record_exception(e)
                span.set_attribute(ToolAttributes.TOOL_STATUS, "error")
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    return wrapper


def tool_async_wrapper(tracer, meter):
    """Wrapper for async tool execution."""

    async def wrapper(wrapped, instance, args, kwargs):
        tool_name = getattr(instance, "name", "unnamed_tool")
        span_name = f"tool.arun: {tool_name}"

        tool_input = args[0] if args else kwargs.get("input", "")

        with tracer.start_as_current_span(
            span_name,
            kind=trace.SpanKind.CLIENT,
            attributes={
                SpanAttributes.AGENTOPS_SPAN_KIND: "tool",
                ToolAttributes.TOOL_NAME: tool_name,
                ToolAttributes.TOOL_PARAMETERS: str(tool_input),
            },
        ) as span:
            try:
                # Get the enclosing agent if available
                agent = getattr(instance, "_agent", None)
                if agent:
                    agent_name = getattr(agent, "name", "unnamed_agent")
                    set_span_attribute(span, "tool.agent", agent_name)

                # Set tool description if available
                if hasattr(instance, "description"):
                    span.set_attribute(ToolAttributes.TOOL_DESCRIPTION, str(instance.description))

                # Create metric for tool usage
                tool_usage_counter = meter.create_counter(
                    name="tool.usage.count",
                    unit="1",
                    description="Number of times a tool is used",
                    attributes={
                        SpanAttributes.LLM_SYSTEM: "crewai",
                        ToolAttributes.TOOL_NAME: tool_name,
                    },
                )
                tool_usage_counter.add(1)

                result = await wrapped(*args, **kwargs)

                span.set_attribute(ToolAttributes.TOOL_RESULT, str(result))
                span.set_attribute(ToolAttributes.TOOL_STATUS, "success")
                span.set_status(Status(StatusCode.OK))

                return result
            except Exception as e:
                span.record_exception(e)
                span.set_attribute(ToolAttributes.TOOL_STATUS, "error")
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    return wrapper


def tool_run_wrapper(tracer, meter):
    """Wrapper for tool run method."""
    return tool_wrapper(tracer, meter)  # Same logic


def tool_calling_wrapper(tracer):
    """Wrapper for tool_calling function."""

    def wrapper(wrapped, instance, args, kwargs):
        # Extract tool name and calling information
        tool_name = "unknown"
        calling = None

        if args:
            calling = args[0]
            if hasattr(calling, "tool_name"):
                tool_name = calling.tool_name

        span_name = f"tool.calling: {tool_name}"

        with tracer.start_as_current_span(
            span_name,
            kind=trace.SpanKind.CLIENT,
            attributes={
                SpanAttributes.AGENTOPS_SPAN_KIND: "tool.usage",
                ToolAttributes.TOOL_NAME: tool_name,
            },
        ) as span:
            try:
                # Log tool arguments if available
                if calling and hasattr(calling, "arguments") and calling.arguments:
                    span.set_attribute(ToolAttributes.TOOL_PARAMETERS, str(calling.arguments))

                result = wrapped(*args, **kwargs)

                span.set_attribute(ToolAttributes.TOOL_RESULT, str(result))
                span.set_attribute(ToolAttributes.TOOL_STATUS, "success")
                span.set_status(Status(StatusCode.OK))

                return result
            except Exception as e:
                span.record_exception(e)
                span.set_attribute(ToolAttributes.TOOL_STATUS, "error")
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    return wrapper
