"""Attribute extractors for SmoLAgents agent operations."""

from typing import Any, Dict, Optional, Tuple
import uuid
import json

from agentops.instrumentation.common.attributes import get_common_attributes
from agentops.semconv.agent import AgentAttributes
from agentops.semconv.tool import ToolAttributes
from agentops.semconv.message import MessageAttributes
from agentops.semconv.span_attributes import SpanAttributes


def get_agent_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> Dict[str, Any]:
    """Extract attributes from an agent execution.

    Args:
        args: Optional tuple of positional arguments
        kwargs: Optional dict of keyword arguments
        return_value: Optional return value from the wrapped function

    Returns:
        Dict containing extracted attributes
    """
    attributes = get_common_attributes()

    # Extract agent info from instance
    if args and len(args) > 0:
        instance = args[0]
        agent_type = instance.__class__.__name__

        # Get tools and managed agents
        tools = []
        if hasattr(instance, "tools") and instance.tools:
            tools = list(instance.tools.keys())
        managed_agents = []
        if hasattr(instance, "managed_agents") and instance.managed_agents:
            managed_agents = list(instance.managed_agents.keys())

        # Get model info
        model_id = None
        if hasattr(instance, "model") and hasattr(instance.model, "model_id"):
            model_id = instance.model.model_id

        attributes.update(
            {
                AgentAttributes.AGENT_ID: str(uuid.uuid4()),
                AgentAttributes.AGENT_NAME: agent_type,
                AgentAttributes.AGENT_ROLE: "executor",
                AgentAttributes.AGENT_TOOLS: tools,
                "agent.managed_agents": managed_agents,
            }
        )

        # Only add attributes if they have non-None values
        max_steps = getattr(instance, "max_steps", None)
        if max_steps is not None:
            attributes["agent.max_steps"] = max_steps

        planning_interval = getattr(instance, "planning_interval", None)
        if planning_interval is not None:
            attributes["agent.planning_interval"] = planning_interval

        if model_id:
            attributes[SpanAttributes.LLM_REQUEST_MODEL] = model_id

    # Extract task from kwargs or args
    if kwargs:
        task = kwargs.get("task")
        stream = kwargs.get("stream", False)
        reset = kwargs.get("reset", True)
        max_steps = kwargs.get("max_steps")
        additional_args = kwargs.get("additional_args")

        if task:
            attributes[AgentAttributes.AGENT_REASONING] = task
        attributes["agent.stream_mode"] = stream
        attributes["agent.reset"] = reset
        if max_steps is not None:
            attributes["agent.max_steps_override"] = max_steps
        if additional_args:
            attributes["agent.additional_args"] = json.dumps(additional_args)
    elif args and len(args) > 1:
        attributes[AgentAttributes.AGENT_REASONING] = args[1]

    # Handle return value for full result mode
    if return_value is not None:
        if hasattr(return_value, "output"):
            # RunResult object
            attributes[SpanAttributes.AGENTOPS_ENTITY_OUTPUT] = str(return_value.output)
            attributes["agent.result_state"] = return_value.state
            if return_value.token_usage:
                attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = return_value.token_usage.input_tokens
                attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = return_value.token_usage.output_tokens
                attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = (
                    return_value.token_usage.input_tokens + return_value.token_usage.output_tokens
                )
        else:
            attributes[SpanAttributes.AGENTOPS_ENTITY_OUTPUT] = str(return_value)

    return attributes


def get_agent_stream_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> Dict[str, Any]:
    """Extract attributes from agent streaming execution.

    Args:
        args: Optional tuple of positional arguments
        kwargs: Optional dict of keyword arguments
        return_value: Optional return value from the wrapped function

    Returns:
        Dict containing extracted attributes
    """
    attributes = get_common_attributes()

    # Extract agent info from instance
    if args and len(args) > 0:
        instance = args[0]
        agent_type = instance.__class__.__name__

        attributes.update(
            {
                AgentAttributes.AGENT_NAME: agent_type,
                AgentAttributes.AGENT_ROLE: "executor",
                "agent.stream_mode": True,
            }
        )

    # Extract task and parameters
    if kwargs:
        task = kwargs.get("task")
        max_steps = kwargs.get("max_steps")

        if task:
            attributes[AgentAttributes.AGENT_REASONING] = task
        if max_steps:
            attributes["agent.max_steps"] = max_steps

    return attributes


def get_agent_step_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> Dict[str, Any]:
    """Extract attributes from an agent step execution.

    Args:
        args: Optional tuple of positional arguments
        kwargs: Optional dict of keyword arguments
        return_value: Optional return value from the wrapped function

    Returns:
        Dict containing extracted attributes
    """
    attributes = get_common_attributes()

    # Extract agent info from instance
    if args and len(args) > 0:
        instance = args[0]
        agent_type = instance.__class__.__name__

        attributes.update(
            {
                AgentAttributes.AGENT_NAME: agent_type,
                "agent.step_number": getattr(instance, "step_number", 0),
            }
        )

    # Extract memory step info
    if args and len(args) > 1:
        memory_step = args[1]
        if hasattr(memory_step, "step_number"):
            attributes["step.number"] = memory_step.step_number
        if hasattr(memory_step, "tool_calls") and memory_step.tool_calls:
            # Extract tool call info
            for i, tool_call in enumerate(memory_step.tool_calls):
                attributes.update(
                    {
                        MessageAttributes.TOOL_CALL_ID.format(i=i): tool_call.id,
                        MessageAttributes.TOOL_CALL_NAME.format(i=i): tool_call.name,
                        MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=i): json.dumps(tool_call.arguments),
                    }
                )
        if hasattr(memory_step, "error") and memory_step.error:
            attributes["step.error"] = str(memory_step.error)
        if hasattr(memory_step, "observations"):
            attributes["step.observations"] = str(memory_step.observations)

    # Handle return value
    if return_value is not None:
        attributes[SpanAttributes.AGENTOPS_ENTITY_OUTPUT] = str(return_value)

    return attributes


def get_tool_call_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> Dict[str, Any]:
    """Extract attributes from a tool call.

    Args:
        args: Optional tuple of positional arguments
        kwargs: Optional dict of keyword arguments
        return_value: Optional return value from the wrapped function

    Returns:
        Dict containing extracted attributes
    """
    attributes = get_common_attributes()

    # Extract tool call information
    tool_call = None
    if kwargs and "tool_call" in kwargs:
        tool_call = kwargs["tool_call"]
    elif args and len(args) > 1:
        tool_call = args[1]

    if tool_call:
        # Extract tool call details
        tool_id = str(uuid.uuid4())
        tool_name = "unknown"
        tool_arguments = {}

        if hasattr(tool_call, "id"):
            tool_id = tool_call.id
        if hasattr(tool_call, "name"):
            tool_name = tool_call.name
        elif hasattr(tool_call, "function") and hasattr(tool_call.function, "name"):
            tool_name = tool_call.function.name

        if hasattr(tool_call, "arguments"):
            tool_arguments = tool_call.arguments
        elif hasattr(tool_call, "function") and hasattr(tool_call.function, "arguments"):
            try:
                tool_arguments = (
                    json.loads(tool_call.function.arguments)
                    if isinstance(tool_call.function.arguments, str)
                    else tool_call.function.arguments
                )
            except (json.JSONDecodeError, TypeError):
                tool_arguments = {"raw": str(tool_call.function.arguments)}

        attributes.update(
            {
                ToolAttributes.TOOL_ID: tool_id,
                ToolAttributes.TOOL_NAME: tool_name,
                ToolAttributes.TOOL_PARAMETERS: json.dumps(tool_arguments),
                ToolAttributes.TOOL_STATUS: "pending",
                ToolAttributes.TOOL_DESCRIPTION: "unknown",
            }
        )

    # Extract instance information for Tool.__call__ style calls
    if args and len(args) > 0:
        instance = args[0]
        if hasattr(instance, "__class__") and instance.__class__.__name__ in ["Tool", "DuckDuckGoSearchTool"]:
            tool_name = getattr(instance, "name", instance.__class__.__name__)
            tool_description = getattr(instance, "description", "unknown")

            # Update attributes with instance info
            attributes.update(
                {
                    ToolAttributes.TOOL_NAME: tool_name,
                    ToolAttributes.TOOL_DESCRIPTION: tool_description,
                }
            )

            # If there are additional args, they might be tool inputs
            if len(args) > 1:
                tool_inputs = {}
                for i, arg in enumerate(args[1:], 1):
                    tool_inputs[f"arg_{i}"] = str(arg)
                attributes[ToolAttributes.TOOL_PARAMETERS] = json.dumps(tool_inputs)

    # Handle return value
    if return_value is not None:
        attributes[ToolAttributes.TOOL_STATUS] = "success"
        # Store the result if it's not too large
        result_str = str(return_value)
        if len(result_str) > 1000:
            result_str = result_str[:1000] + "..."
        attributes[ToolAttributes.TOOL_RESULT] = result_str

    return attributes


def get_planning_step_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> Dict[str, Any]:
    """Extract attributes from a planning step.

    Args:
        args: Optional tuple of positional arguments
        kwargs: Optional dict of keyword arguments
        return_value: Optional return value from the wrapped function

    Returns:
        Dict containing extracted attributes
    """
    attributes = get_common_attributes()

    # Extract agent info from instance
    if args and len(args) > 0:
        instance = args[0]
        agent_type = instance.__class__.__name__

        attributes.update(
            {
                AgentAttributes.AGENT_NAME: agent_type,
                "planning.agent_type": agent_type,
            }
        )

    # Extract planning step info from args
    if args and len(args) > 1:
        task = args[1]
        attributes[AgentAttributes.AGENT_REASONING] = task

    # Extract kwargs
    if kwargs:
        is_first_step = kwargs.get("is_first_step", False)
        step = kwargs.get("step", 0)

        attributes.update(
            {
                "planning.is_first_step": is_first_step,
                "planning.step_number": step,
            }
        )

    # Handle generator return value
    if return_value is not None:
        # The return value is typically a generator for planning steps
        attributes["planning.status"] = "completed"

    return attributes


def get_managed_agent_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> Dict[str, Any]:
    """Extract attributes from a managed agent call.

    Args:
        args: Optional tuple of positional arguments
        kwargs: Optional dict of keyword arguments
        return_value: Optional return value from the wrapped function

    Returns:
        Dict containing extracted attributes
    """
    attributes = get_common_attributes()

    # Extract agent info from instance
    if args and len(args) > 0:
        instance = args[0]
        agent_type = instance.__class__.__name__
        agent_name = getattr(instance, "name", agent_type)
        agent_description = getattr(instance, "description", "")

        attributes.update(
            {
                AgentAttributes.AGENT_ID: str(uuid.uuid4()),
                AgentAttributes.AGENT_NAME: agent_name,
                AgentAttributes.AGENT_ROLE: "managed",
                "agent.type": agent_type,
                "agent.description": agent_description,
                "agent.provide_run_summary": getattr(instance, "provide_run_summary", False),
            }
        )

    # Extract task
    if args and len(args) > 1:
        task = args[1]
        attributes[AgentAttributes.AGENT_REASONING] = task
    elif kwargs and "task" in kwargs:
        attributes[AgentAttributes.AGENT_REASONING] = kwargs["task"]

    # Handle return value
    if return_value is not None:
        if isinstance(return_value, dict):
            # Managed agent typically returns a dict with task and output
            attributes[SpanAttributes.AGENTOPS_ENTITY_OUTPUT] = json.dumps(return_value)
        else:
            attributes[SpanAttributes.AGENTOPS_ENTITY_OUTPUT] = str(return_value)

    return attributes
