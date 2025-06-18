"""Attribute extractors for SmoLAgents agent operations."""

from typing import Any, Dict, Optional, Tuple
import uuid
import json

from agentops.instrumentation.common.attributes import get_common_attributes
from agentops.semconv.agent import AgentAttributes
from agentops.semconv.tool import ToolAttributes


def get_agent_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> Dict[str, Any]:
    """Extract attributes from an agent execution call.

    Args:
        args: Optional tuple of positional arguments
        kwargs: Optional dict of keyword arguments
        return_value: Optional return value from the function

    Returns:
        Dictionary of extracted attributes
    """
    attributes = get_common_attributes()

    try:
        # Extract agent instance information
        agent_instance = None
        if args and len(args) > 0:
            agent_instance = args[0]
        elif kwargs and "self" in kwargs:
            agent_instance = kwargs["self"]

        if agent_instance:
            # Extract agent name
            agent_name = getattr(agent_instance, "name", agent_instance.__class__.__name__)
            attributes[AgentAttributes.AGENT_NAME] = agent_name

            # Generate agent ID if not present
            agent_id = getattr(agent_instance, "id", str(uuid.uuid4()))
            attributes[AgentAttributes.AGENT_ID] = agent_id

            # Extract agent role/type
            attributes[AgentAttributes.AGENT_ROLE] = "executor"

            # Extract tools information
            tools = getattr(agent_instance, "tools", [])
            if tools:
                tool_names = []
                for tool in tools:
                    tool_name = getattr(tool, "name", str(tool))
                    tool_names.append(tool_name)
                attributes[AgentAttributes.AGENT_TOOLS] = json.dumps(tool_names)
            else:
                attributes[AgentAttributes.AGENT_TOOLS] = "[]"

            # Extract managed agents information
            managed_agents = getattr(agent_instance, "managed_agents", [])
            if managed_agents:
                managed_agent_names = []
                for managed_agent in managed_agents:
                    agent_name = getattr(managed_agent, "name", managed_agent.__class__.__name__)
                    managed_agent_names.append(agent_name)
                attributes[AgentAttributes.AGENT_MANAGED_AGENTS] = json.dumps(managed_agent_names)
            else:
                attributes[AgentAttributes.AGENT_MANAGED_AGENTS] = "[]"

        # Extract input/task from args or kwargs
        task_input = None
        if args and len(args) > 1:
            task_input = args[1]
        elif kwargs and "task" in kwargs:
            task_input = kwargs["task"]
        elif kwargs and "prompt" in kwargs:
            task_input = kwargs["prompt"]

        if task_input:
            attributes["agent.task"] = str(task_input)

        # Extract return value/output
        if return_value is not None:
            attributes["agentops.entity.output"] = str(return_value)

    except Exception:
        # If extraction fails, continue with basic attributes
        pass

    return attributes


def get_agent_stream_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> Dict[str, Any]:
    """Extract attributes from an agent streaming call.

    Args:
        args: Optional tuple of positional arguments
        kwargs: Optional dict of keyword arguments
        return_value: Optional return value from the function

    Returns:
        Dictionary of extracted attributes
    """
    attributes = get_common_attributes()

    try:
        # Extract reasoning/task information
        if kwargs:
            if "max_steps" in kwargs:
                attributes["agent.max_steps"] = str(kwargs["max_steps"])

            # Extract task/reasoning from various parameter names
            task_info = None
            for param_name in ["task", "prompt", "reasoning", "query"]:
                if param_name in kwargs:
                    task_info = kwargs[param_name]
                    break

            if task_info:
                attributes["agent.reasoning"] = str(task_info)

        # Extract from args
        if args and len(args) > 1:
            task_info = args[1]
            attributes["agent.reasoning"] = str(task_info)

    except Exception:
        # If extraction fails, continue with basic attributes
        pass

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
        return_value: Optional return value from the function

    Returns:
        Dictionary of extracted attributes
    """
    attributes = get_common_attributes()

    try:
        # Try to extract step information
        step_number = getattr(args[0] if args else None, "step_count", None)
        if step_number is not None:
            attributes["agent.step_number"] = str(step_number)

        # Extract step name/type
        step_name = "ActionStep"  # Default for smolagents
        attributes["agent.name"] = step_name

        # Extract return value
        if return_value is not None:
            attributes["agentops.entity.output"] = str(return_value)

    except Exception:
        # If extraction fails, continue with basic attributes
        pass

    return attributes


def get_tool_call_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> Dict[str, Any]:
    """Extract attributes from a tool call execution.

    Args:
        args: Optional tuple of positional arguments
        kwargs: Optional dict of keyword arguments
        return_value: Optional return value from the function

    Returns:
        Dictionary of extracted attributes
    """
    attributes = get_common_attributes()

    try:
        # Generate tool execution ID
        tool_id = str(uuid.uuid4())
        attributes[ToolAttributes.TOOL_ID] = tool_id

        # Extract tool information from various sources
        tool_name = "unknown"
        tool_description = "unknown"
        tool_parameters = "{}"

        # Try to extract from instance (first arg)
        if args and len(args) > 0:
            instance = args[0]
            if hasattr(instance, "name"):
                tool_name = instance.name
            if hasattr(instance, "description"):
                tool_description = instance.description

        # Try to extract from kwargs
        if kwargs:
            if "tool_call" in kwargs:
                tool_call = kwargs["tool_call"]
                if hasattr(tool_call, "function"):
                    tool_name = tool_call.function.name
                    if hasattr(tool_call.function, "arguments"):
                        tool_parameters = tool_call.function.arguments
            elif "name" in kwargs:
                tool_name = kwargs["name"]
            elif "function_name" in kwargs:
                tool_name = kwargs["function_name"]

            # Extract parameters
            if "parameters" in kwargs:
                tool_parameters = json.dumps(kwargs["parameters"])
            elif "arguments" in kwargs:
                tool_parameters = json.dumps(kwargs["arguments"])
            elif "args" in kwargs:
                tool_parameters = json.dumps(kwargs["args"])

        # Set tool attributes
        attributes[ToolAttributes.TOOL_NAME] = tool_name
        attributes[ToolAttributes.TOOL_DESCRIPTION] = tool_description
        attributes[ToolAttributes.TOOL_PARAMETERS] = tool_parameters
        attributes[ToolAttributes.TOOL_STATUS] = "pending"
        attributes[ToolAttributes.TOOL_OUTPUT_TYPE] = "unknown"
        attributes[ToolAttributes.TOOL_INPUTS] = "{}"

        # Extract return value
        if return_value is not None:
            attributes["tool.result"] = str(return_value)
            attributes[ToolAttributes.TOOL_STATUS] = "success"

    except Exception:
        # If extraction fails, set basic attributes
        attributes[ToolAttributes.TOOL_NAME] = "unknown"
        attributes[ToolAttributes.TOOL_DESCRIPTION] = "unknown"
        attributes[ToolAttributes.TOOL_ID] = str(uuid.uuid4())
        attributes[ToolAttributes.TOOL_PARAMETERS] = "{}"
        attributes[ToolAttributes.TOOL_STATUS] = "pending"

    return attributes


def get_planning_step_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> Dict[str, Any]:
    """Extract attributes from a planning step execution.

    Args:
        args: Optional tuple of positional arguments
        kwargs: Optional dict of keyword arguments
        return_value: Optional return value from the function

    Returns:
        Dictionary of extracted attributes
    """
    attributes = get_common_attributes()

    try:
        # Extract planning information
        if kwargs:
            if "planning_step" in kwargs:
                step = kwargs["planning_step"]
                attributes["agent.planning.step"] = str(step)
            if "reasoning" in kwargs:
                attributes["agent.planning.reasoning"] = str(kwargs["reasoning"])

        # Extract return value
        if return_value is not None:
            attributes["agentops.entity.output"] = str(return_value)

    except Exception:
        # If extraction fails, continue with basic attributes
        pass

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
        return_value: Optional return value from the function

    Returns:
        Dictionary of extracted attributes
    """
    attributes = get_common_attributes()

    try:
        # Extract managed agent information
        agent_instance = None
        if args and len(args) > 0:
            agent_instance = args[0]
        elif kwargs and "agent" in kwargs:
            agent_instance = kwargs["agent"]

        if agent_instance:
            # Extract agent details
            agent_name = getattr(agent_instance, "name", agent_instance.__class__.__name__)
            agent_id = getattr(agent_instance, "id", str(uuid.uuid4()))
            agent_description = getattr(agent_instance, "description", "")

            attributes[AgentAttributes.AGENT_NAME] = agent_name
            attributes[AgentAttributes.AGENT_ID] = agent_id
            attributes[AgentAttributes.AGENT_ROLE] = "managed"
            attributes[AgentAttributes.AGENT_TYPE] = agent_instance.__class__.__name__

            if agent_description:
                attributes[AgentAttributes.AGENT_DESCRIPTION] = agent_description

            # Check if this agent provides run summaries
            attributes["agent.provide_run_summary"] = "false"  # Default for smolagents

        # Extract task information
        task = None
        if args and len(args) > 1:
            task = args[1]
        elif kwargs and "task" in kwargs:
            task = kwargs["task"]

        if task:
            attributes["agent.task"] = str(task)

        # Extract return value
        if return_value is not None:
            attributes["agentops.entity.output"] = str(return_value)

    except Exception:
        # If extraction fails, continue with basic attributes
        pass

    return attributes
