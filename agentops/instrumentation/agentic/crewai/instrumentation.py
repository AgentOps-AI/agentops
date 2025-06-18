import os
import time
import logging
from typing import Dict, Any
from contextlib import contextmanager

from opentelemetry.trace import SpanKind, get_current_span
from opentelemetry.metrics import Meter
from opentelemetry.instrumentation.utils import unwrap

from agentops.instrumentation.common import (
    CommonInstrumentor,
    InstrumentorConfig,
    StandardMetrics,
    create_wrapper_factory,
    create_span,
    SpanAttributeManager,
    safe_set_attribute,
    set_token_usage_attributes,
    TokenUsageExtractor,
)
from agentops.instrumentation.agentic.crewai.version import __version__
from agentops.semconv import SpanAttributes, AgentOpsSpanKindValues, ToolAttributes, MessageAttributes
from agentops.semconv.core import CoreAttributes
from agentops.instrumentation.agentic.crewai.crewai_span_attributes import CrewAISpanAttributes, set_span_attribute
from agentops import get_client

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


class CrewaiInstrumentor(CommonInstrumentor):
    """Instrumentor for CrewAI framework."""

    def __init__(self):
        config = InstrumentorConfig(
            library_name="crewai",
            library_version=__version__,
            wrapped_methods=[],  # We'll use custom wrapping for CrewAI
            metrics_enabled=is_metrics_enabled(),
            dependencies=_instruments,
        )
        super().__init__(config)
        self._attribute_manager = None

    def _initialize(self, **kwargs):
        """Initialize attribute manager."""
        application_name = kwargs.get("application_name", "default_application")
        environment = kwargs.get("environment", "default_environment")
        self._attribute_manager = SpanAttributeManager(
            service_name=application_name, deployment_environment=environment
        )

    def _create_metrics(self, meter: Meter) -> Dict[str, Any]:
        """Create metrics for CrewAI instrumentation."""
        return StandardMetrics.create_standard_metrics(meter)

    def _custom_wrap(self, **kwargs):
        """Perform custom wrapping for CrewAI methods."""
        from wrapt import wrap_function_wrapper

        # Get attribute manager for all wrappers
        attr_manager = self._attribute_manager

        # Define wrappers using the new create_wrapper_factory
        wrap_function_wrapper(
            "crewai.crew",
            "Crew.kickoff",
            create_wrapper_factory(wrap_kickoff_impl, self._metrics, attr_manager)(self._tracer),
        )

        wrap_function_wrapper(
            "crewai.agent",
            "Agent.execute_task",
            create_wrapper_factory(wrap_agent_execute_task_impl, self._metrics, attr_manager)(self._tracer),
        )

        wrap_function_wrapper(
            "crewai.task",
            "Task.execute_sync",
            create_wrapper_factory(wrap_task_execute_impl, self._metrics, attr_manager)(self._tracer),
        )

        wrap_function_wrapper(
            "crewai.llm",
            "LLM.call",
            create_wrapper_factory(wrap_llm_call_impl, self._metrics, attr_manager)(self._tracer),
        )

        wrap_function_wrapper(
            "crewai.utilities.tool_utils",
            "execute_tool_and_check_finality",
            create_wrapper_factory(wrap_tool_execution_impl, self._metrics, attr_manager)(self._tracer),
        )

        wrap_function_wrapper(
            "crewai.tools.tool_usage",
            "ToolUsage.use",
            create_wrapper_factory(wrap_tool_usage_impl, self._metrics, attr_manager)(self._tracer),
        )

    def _custom_unwrap(self, **kwargs):
        """Perform custom unwrapping for CrewAI methods."""
        unwrap("crewai.crew", "Crew.kickoff")
        unwrap("crewai.agent", "Agent.execute_task")
        unwrap("crewai.task", "Task.execute_sync")
        unwrap("crewai.llm", "LLM.call")
        unwrap("crewai.utilities.tool_utils", "execute_tool_and_check_finality")
        unwrap("crewai.tools.tool_usage", "ToolUsage.use")


# Implementation functions for wrappers
def wrap_kickoff_impl(tracer, metrics, attr_manager, wrapped, instance, args, kwargs):
    """Implementation of kickoff wrapper."""
    logger.debug(
        f"CrewAI: Starting workflow instrumentation for Crew with {len(getattr(instance, 'agents', []))} agents"
    )

    config = get_client().config
    attributes = {
        SpanAttributes.LLM_SYSTEM: "crewai",
    }

    if config.default_tags and len(config.default_tags) > 0:
        tag_list = list(config.default_tags)
        attributes[CoreAttributes.TAGS] = tag_list

    # Use trace_name from config if available, otherwise default to "crewai.workflow"
    span_name = config.trace_name if config.trace_name else "crewai.workflow"

    with create_span(
        tracer, span_name, kind=SpanKind.INTERNAL, attributes=attributes, attribute_manager=attr_manager
    ) as span:
        logger.debug("CrewAI: Processing crew instance attributes")

        # First set general crew attributes but skip agent processing
        crew_attrs = CrewAISpanAttributes(span=span, instance=instance, skip_agent_processing=True)

        # Prioritize agent processing before task execution
        if hasattr(instance, "agents") and instance.agents:
            logger.debug(f"CrewAI: Explicitly processing {len(instance.agents)} agents before task execution")
            crew_attrs._parse_agents(instance.agents)

        logger.debug("CrewAI: Executing wrapped crew kickoff function")
        result = wrapped(*args, **kwargs)

        if result:
            class_name = instance.__class__.__name__
            span.set_attribute(f"crewai.{class_name.lower()}.result", str(result))

            if class_name == "Crew":
                _process_crew_result(span, instance, result)

                # Set token usage using common utilities
                set_token_usage_attributes(span, result)
                _calculate_efficiency_metrics(span, result)

        return result


def _process_crew_result(span, instance, result):
    """Process crew execution result."""
    if hasattr(result, "usage_metrics"):
        span.set_attribute("crewai.crew.usage_metrics", str(getattr(result, "usage_metrics")))

    if hasattr(result, "tasks_output") and result.tasks_output:
        span.set_attribute("crewai.crew.tasks_output", str(result.tasks_output))

        try:
            task_details_by_description = _build_task_details_map(instance)
            _process_task_outputs(span, result.tasks_output, task_details_by_description)
        except Exception as ex:
            logger.warning(f"Failed to parse task outputs: {ex}")


def _build_task_details_map(instance):
    """Build a map of task descriptions to task details."""
    task_details_by_description = {}
    if hasattr(instance, "tasks"):
        for task in instance.tasks:
            if task is not None:
                agent_id = ""
                agent_role = ""
                if hasattr(task, "agent") and task.agent:
                    agent_id = str(getattr(task.agent, "id", ""))
                    agent_role = getattr(task.agent, "role", "")

                tools = []
                if hasattr(task, "tools") and task.tools:
                    for tool in task.tools:
                        tool_info = {}
                        if hasattr(tool, "name"):
                            tool_info["name"] = tool.name
                        if hasattr(tool, "description"):
                            tool_info["description"] = tool.description
                        if tool_info:
                            tools.append(tool_info)

                task_details_by_description[task.description] = {
                    "agent_id": agent_id,
                    "agent_role": agent_role,
                    "async_execution": getattr(task, "async_execution", False),
                    "human_input": getattr(task, "human_input", False),
                    "output_file": getattr(task, "output_file", ""),
                    "tools": tools,
                }
    return task_details_by_description


def _process_task_outputs(span, tasks_output, task_details_by_description):
    """Process task outputs and set attributes."""
    for idx, task_output in enumerate(tasks_output):
        task_prefix = f"crewai.crew.tasks.{idx}"

        task_attrs = {
            "description": getattr(task_output, "description", ""),
            "name": getattr(task_output, "name", ""),
            "expected_output": getattr(task_output, "expected_output", ""),
            "summary": getattr(task_output, "summary", ""),
            "raw": getattr(task_output, "raw", ""),
            "agent": getattr(task_output, "agent", ""),
            "output_format": str(getattr(task_output, "output_format", "")),
        }

        for attr_name, attr_value in task_attrs.items():
            if attr_value:
                safe_set_attribute(span, f"{task_prefix}.{attr_name}", attr_value, max_length=1000)

        span.set_attribute(f"{task_prefix}.status", "completed")
        span.set_attribute(f"{task_prefix}.id", str(idx))

        description = task_attrs.get("description", "")
        if description and description in task_details_by_description:
            details = task_details_by_description[description]

            span.set_attribute(f"{task_prefix}.agent_id", details["agent_id"])
            span.set_attribute(f"{task_prefix}.async_execution", str(details["async_execution"]))
            span.set_attribute(f"{task_prefix}.human_input", str(details["human_input"]))

            if details["output_file"]:
                span.set_attribute(f"{task_prefix}.output_file", details["output_file"])

            for tool_idx, tool in enumerate(details["tools"]):
                for tool_key, tool_value in tool.items():
                    span.set_attribute(f"{task_prefix}.tools.{tool_idx}.{tool_key}", str(tool_value))


def _calculate_efficiency_metrics(span, result):
    """Calculate and set efficiency metrics."""
    if hasattr(result, "token_usage"):
        try:
            usage = TokenUsageExtractor.extract_from_response(result)

            # Calculate efficiency
            if usage.prompt_tokens and usage.completion_tokens and usage.prompt_tokens > 0:
                efficiency = usage.completion_tokens / usage.prompt_tokens
                span.set_attribute("crewai.crew.token_efficiency", f"{efficiency:.4f}")

            # Calculate cache efficiency
            if usage.cached_prompt_tokens and usage.prompt_tokens and usage.prompt_tokens > 0:
                cache_ratio = usage.cached_prompt_tokens / usage.prompt_tokens
                span.set_attribute("crewai.crew.cache_efficiency", f"{cache_ratio:.4f}")

        except Exception as ex:
            logger.warning(f"Failed to calculate efficiency metrics: {ex}")


def wrap_agent_execute_task_impl(tracer, metrics, attr_manager, wrapped, instance, args, kwargs):
    """Implementation of agent execute task wrapper."""
    agent_name = instance.role if hasattr(instance, "role") else "agent"

    with create_span(
        tracer,
        f"{agent_name}.agent",
        kind=SpanKind.CLIENT,
        attributes={
            SpanAttributes.AGENTOPS_SPAN_KIND: AgentOpsSpanKindValues.AGENT.value,
        },
        attribute_manager=attr_manager,
    ) as span:
        CrewAISpanAttributes(span=span, instance=instance)

        result = wrapped(*args, **kwargs)

        attach_tool_executions_to_agent_span(span)

        # Record token metrics if available
        if metrics.get("token_histogram") and hasattr(instance, "_token_process"):
            token_process = instance._token_process.get_summary()
            if hasattr(token_process, "prompt_tokens"):
                metrics["token_histogram"].record(
                    token_process.prompt_tokens,
                    attributes={
                        SpanAttributes.LLM_SYSTEM: "crewai",
                        SpanAttributes.LLM_TOKEN_TYPE: "input",
                        SpanAttributes.LLM_RESPONSE_MODEL: str(instance.llm.model),
                    },
                )
            if hasattr(token_process, "completion_tokens"):
                metrics["token_histogram"].record(
                    token_process.completion_tokens,
                    attributes={
                        SpanAttributes.LLM_SYSTEM: "crewai",
                        SpanAttributes.LLM_TOKEN_TYPE: "output",
                        SpanAttributes.LLM_RESPONSE_MODEL: str(instance.llm.model),
                    },
                )

        if hasattr(instance, "llm") and hasattr(instance.llm, "model"):
            set_span_attribute(span, SpanAttributes.LLM_REQUEST_MODEL, str(instance.llm.model))
            set_span_attribute(span, SpanAttributes.LLM_RESPONSE_MODEL, str(instance.llm.model))

        return result


def wrap_task_execute_impl(tracer, metrics, attr_manager, wrapped, instance, args, kwargs):
    """Implementation of task execute wrapper."""
    task_name = instance.description if hasattr(instance, "description") else "task"

    config = get_client().config
    attributes = {
        SpanAttributes.AGENTOPS_SPAN_KIND: AgentOpsSpanKindValues.TASK.value,
    }

    if config.default_tags and len(config.default_tags) > 0:
        tag_list = list(config.default_tags)
        attributes[CoreAttributes.TAGS] = tag_list

    with create_span(
        tracer, f"{task_name}.task", kind=SpanKind.CLIENT, attributes=attributes, attribute_manager=attr_manager
    ) as span:
        CrewAISpanAttributes(span=span, instance=instance)

        result = wrapped(*args, **kwargs)

        set_span_attribute(span, SpanAttributes.AGENTOPS_ENTITY_OUTPUT, str(result))
        return result


def wrap_llm_call_impl(tracer, metrics, attr_manager, wrapped, instance, args, kwargs):
    """Implementation of LLM call wrapper."""
    llm = instance.model if hasattr(instance, "model") else "llm"
    start_time = time.time()

    with create_span(tracer, f"{llm}.llm", kind=SpanKind.CLIENT, attribute_manager=attr_manager) as span:
        CrewAISpanAttributes(span=span, instance=instance)

        result = wrapped(*args, **kwargs)

        # Set prompt attributes from args
        if args and isinstance(args[0], list):
            for i, message in enumerate(args[0]):
                if isinstance(message, dict):
                    if "role" in message:
                        span.set_attribute(MessageAttributes.PROMPT_ROLE.format(i=i), message["role"])
                    if "content" in message:
                        span.set_attribute(MessageAttributes.PROMPT_CONTENT.format(i=i), message["content"])

        # Set completion attributes from result
        if result:
            span.set_attribute(MessageAttributes.COMPLETION_CONTENT.format(i=0), str(result))
            span.set_attribute(MessageAttributes.COMPLETION_ROLE.format(i=0), "assistant")

        # Set token usage attributes from callbacks
        if "callbacks" in kwargs and kwargs["callbacks"] and hasattr(kwargs["callbacks"][0], "token_cost_process"):
            token_process = kwargs["callbacks"][0].token_cost_process
            if hasattr(token_process, "completion_tokens"):
                span.set_attribute(SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, token_process.completion_tokens)
            if hasattr(token_process, "prompt_tokens"):
                span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, token_process.prompt_tokens)
            if hasattr(token_process, "total_tokens"):
                span.set_attribute(SpanAttributes.LLM_USAGE_TOTAL_TOKENS, token_process.total_tokens)

        # Record duration metric
        if metrics.get("duration_histogram"):
            duration = time.time() - start_time
            metrics["duration_histogram"].record(
                duration,
                attributes={
                    SpanAttributes.LLM_SYSTEM: "crewai",
                    SpanAttributes.LLM_RESPONSE_MODEL: str(instance.model),
                },
            )

        return result


def wrap_tool_execution_impl(tracer, metrics, attr_manager, wrapped, instance, args, kwargs):
    """Implementation of tool execution wrapper."""
    agent_action = args[0] if args else None
    tools = args[1] if len(args) > 1 else []

    if not agent_action:
        return wrapped(*args, **kwargs)

    tool_name = getattr(agent_action, "tool", "unknown_tool")
    tool_input = getattr(agent_action, "tool_input", "")

    with store_tool_execution() as tool_details:
        tool_details["name"] = tool_name
        tool_details["parameters"] = str(tool_input)

        matching_tool = next((tool for tool in tools if hasattr(tool, "name") and tool.name == tool_name), None)
        if matching_tool and hasattr(matching_tool, "description"):
            tool_details["description"] = str(matching_tool.description)

        start_time = time.time()

        with create_span(
            tracer,
            f"{tool_name}.tool",
            kind=SpanKind.CLIENT,
            attributes={
                SpanAttributes.AGENTOPS_SPAN_KIND: "tool",
                ToolAttributes.TOOL_NAME: tool_name,
                ToolAttributes.TOOL_PARAMETERS: str(tool_input),
            },
            attribute_manager=attr_manager,
        ) as span:
            if matching_tool and hasattr(matching_tool, "description"):
                span.set_attribute(ToolAttributes.TOOL_DESCRIPTION, str(matching_tool.description))

            result = wrapped(*args, **kwargs)

            # Record duration metric
            if metrics.get("duration_histogram"):
                duration = time.time() - start_time
                metrics["duration_histogram"].record(
                    duration,
                    attributes={
                        SpanAttributes.LLM_SYSTEM: "crewai",
                        ToolAttributes.TOOL_NAME: tool_name,
                    },
                )

            if hasattr(result, "result"):
                tool_result = str(result.result)
                span.set_attribute(ToolAttributes.TOOL_RESULT, tool_result)
                tool_details["result"] = tool_result

                tool_status = "success" if not hasattr(result, "error") or not result.error else "error"
                span.set_attribute(ToolAttributes.TOOL_STATUS, tool_status)
                tool_details["status"] = tool_status

                if hasattr(result, "error") and result.error:
                    tool_details["error"] = str(result.error)

            duration = time.time() - start_time
            tool_details["duration"] = f"{duration:.3f}"

            return result


def wrap_tool_usage_impl(tracer, metrics, attr_manager, wrapped, instance, args, kwargs):
    """Implementation of tool usage wrapper."""
    calling = args[0] if args else None

    if not calling:
        return wrapped(*args, **kwargs)

    tool_name = getattr(calling, "tool_name", "unknown_tool")

    with store_tool_execution() as tool_details:
        tool_details["name"] = tool_name

        if hasattr(calling, "arguments") and calling.arguments:
            tool_details["parameters"] = str(calling.arguments)

        with create_span(
            tracer,
            f"{tool_name}.tool_usage",
            kind=SpanKind.INTERNAL,
            attributes={
                SpanAttributes.AGENTOPS_SPAN_KIND: "tool.usage",
                ToolAttributes.TOOL_NAME: tool_name,
            },
            attribute_manager=attr_manager,
        ) as span:
            if hasattr(calling, "arguments") and calling.arguments:
                span.set_attribute(ToolAttributes.TOOL_PARAMETERS, str(calling.arguments))

            result = wrapped(*args, **kwargs)

            tool_result = str(result)
            span.set_attribute(ToolAttributes.TOOL_RESULT, tool_result)
            tool_details["result"] = tool_result

            tool_status = "success"
            span.set_attribute(ToolAttributes.TOOL_STATUS, tool_status)
            tool_details["status"] = tool_status

            return result


def is_metrics_enabled() -> bool:
    return (os.getenv("AGENTOPS_METRICS_ENABLED") or "true").lower() == "true"
