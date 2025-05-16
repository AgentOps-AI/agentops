"""Attribute extractors for SmoLAgents agent operations."""

from typing import Any, Dict, Optional, Tuple
import uuid
import time

from agentops.instrumentation.common.attributes import get_common_attributes
from agentops.semconv.agent import AgentAttributes
from agentops.semconv.tool import ToolAttributes


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
        tools = [t.name for t in instance.tools] if hasattr(instance, "tools") else []
        attributes.update(
            {
                AgentAttributes.AGENT_ID: str(uuid.uuid4()),
                AgentAttributes.AGENT_NAME: agent_type,
                AgentAttributes.AGENT_ROLE: "executor",
                AgentAttributes.AGENT_TOOLS: tools,
            }
        )

    # Extract task from kwargs or args
    task = kwargs.get("task", args[1] if len(args) > 1 else "unknown") if kwargs else "unknown"
    attributes[AgentAttributes.AGENT_REASONING] = task

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

    # Extract tool info from instance and args
    if args and len(args) > 0:
        instance = args[0]
        tool_name = instance.name if hasattr(instance, "name") else "unknown"
        tool_description = instance.description if hasattr(instance, "description") else "unknown"

        # Get arguments from args/kwargs
        arguments = {}
        if len(args) > 1:
            arguments = args[1]
        elif kwargs:
            arguments = kwargs

        # Track execution time and success
        start_time = time.time()
        error = None

        try:
            if return_value is not None:
                execution_time = time.time() - start_time
                attributes.update(
                    {
                        ToolAttributes.TOOL_ID: str(uuid.uuid4()),
                        ToolAttributes.TOOL_NAME: tool_name,
                        ToolAttributes.TOOL_DESCRIPTION: tool_description,
                        ToolAttributes.TOOL_PARAMETERS: arguments,
                        ToolAttributes.TOOL_STATUS: "success",
                        ToolAttributes.TOOL_RESULT: str(return_value),
                        "tool.execution_time": execution_time,
                    }
                )
        except Exception as e:
            error = str(e)
            attributes.update(
                {
                    ToolAttributes.TOOL_ID: str(uuid.uuid4()),
                    ToolAttributes.TOOL_NAME: tool_name,
                    ToolAttributes.TOOL_DESCRIPTION: tool_description,
                    ToolAttributes.TOOL_PARAMETERS: arguments,
                    ToolAttributes.TOOL_STATUS: "error",
                    ToolAttributes.TOOL_ERROR: error,
                }
            )

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

    # Extract step info from kwargs
    if kwargs:
        step_number = kwargs.get("step_number", 0)
        is_first_step = kwargs.get("is_first_step", False)
        task = kwargs.get("task", "unknown")

        attributes.update(
            {
                AgentAttributes.AGENT_REASONING: task,
                "planning.step_number": step_number,
                "planning.is_first_step": is_first_step,
            }
        )

    return attributes
