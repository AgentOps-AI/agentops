"""Agno Agent run attributes handler."""

from typing import Optional, Tuple, Dict, Any
from agentops.instrumentation.common.attributes import AttributeMap
from agentops.semconv import SpanAttributes, AgentAttributes, ToolAttributes
from agentops.semconv.span_kinds import SpanKind as AgentOpsSpanKind
import json


def get_agent_run_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract span attributes for Agent.run/arun calls.

    Args:
        args: Positional arguments passed to the run method (self, message, ...)
        kwargs: Keyword arguments passed to the run method
        return_value: The return value from the run method (RunResponse)

    Returns:
        A dictionary of span attributes to be set on the agent span
    """
    attributes: AttributeMap = {}

    # Initialize variables to avoid UnboundLocalError
    agent_name = None

    # Base attributes
    attributes[SpanAttributes.AGENTOPS_SPAN_KIND] = AgentOpsSpanKind.AGENT
    attributes[SpanAttributes.LLM_SYSTEM] = "agno"

    # AgentOps entity attributes
    attributes[SpanAttributes.AGENTOPS_ENTITY_NAME] = "agent"

    # Extract agent information from args[0] (self)
    if args and len(args) >= 1:
        agent = args[0]

        # Core agent identification - set directly at root level
        if hasattr(agent, "agent_id") and agent.agent_id:
            agent_id = str(agent.agent_id)
            attributes[AgentAttributes.AGENT_ID] = agent_id

        if hasattr(agent, "name") and agent.name:
            agent_name = str(agent.name)
            attributes[AgentAttributes.AGENT_NAME] = agent_name

        if hasattr(agent, "role") and agent.role:
            agent_role = str(agent.role)
            attributes[AgentAttributes.AGENT_ROLE] = agent_role

        # Check if agent is part of a team
        if hasattr(agent, "_team") and agent._team:
            team = agent._team
            if hasattr(team, "name") and team.name:
                attributes["agent.parent_team"] = str(team.name)
                attributes["agent.parent_team_display"] = f"Under {team.name}"
            if hasattr(team, "team_id") and team.team_id:
                attributes["agent.parent_team_id"] = str(team.team_id)

        # Model information -
        if hasattr(agent, "model") and agent.model:
            model = agent.model
            if hasattr(model, "id"):
                model_id = str(model.id)
                attributes[SpanAttributes.LLM_REQUEST_MODEL] = model_id
                attributes[SpanAttributes.LLM_RESPONSE_MODEL] = model_id

            if hasattr(model, "provider"):
                model_provider = str(model.provider)
                attributes["agent.model_provider"] = model_provider

        # Agent configuration details - set directly at root level
        if hasattr(agent, "description") and agent.description:
            attributes["agent.description"] = str(agent.description)
        if hasattr(agent, "goal") and agent.goal:
            attributes["agent.goal"] = str(agent.goal)

        if hasattr(agent, "instructions") and agent.instructions:
            if isinstance(agent.instructions, list):
                attributes["agent.instruction"] = " | ".join(str(i) for i in agent.instructions)
            else:
                attributes["agent.instruction"] = str(agent.instructions)
        if hasattr(agent, "expected_output") and agent.expected_output:
            attributes["agent.expected_output"] = str(agent.expected_output)

        if hasattr(agent, "markdown"):
            attributes["agent.markdown"] = str(agent.markdown)

        if hasattr(agent, "reasoning"):
            attributes[AgentAttributes.AGENT_REASONING] = str(agent.reasoning)

        if hasattr(agent, "stream"):
            attributes["agent.stream"] = str(agent.stream)

        if hasattr(agent, "show_tool_calls"):
            attributes["agent.show_tool_calls"] = str(agent.show_tool_calls)

        if hasattr(agent, "tool_call_limit") and agent.tool_call_limit:
            attributes["agent.tool_call_limit"] = str(agent.tool_call_limit)

        # Tools information
        if hasattr(agent, "tools") and agent.tools:
            # Set tool count based on actual number of tools
            attributes["agent.tools_count"] = str(len(agent.tools))

            # Collect all tool names for the AGENT_TOOLS attribute
            tool_names = []

            if len(agent.tools) == 1:
                # Single tool - set directly at root level
                tool = agent.tools[0]
                tool_name = None
                if hasattr(tool, "name"):
                    tool_name = str(tool.name)
                    attributes[ToolAttributes.TOOL_NAME] = tool_name
                elif hasattr(tool, "__name__"):
                    tool_name = str(tool.__name__)
                    attributes[ToolAttributes.TOOL_NAME] = tool_name
                elif callable(tool):
                    tool_name = getattr(tool, "__name__", "unknown_tool")
                    attributes[ToolAttributes.TOOL_NAME] = tool_name

                if tool_name:
                    tool_names.append(tool_name)

                if hasattr(tool, "description") and tool.description:
                    attributes[ToolAttributes.TOOL_DESCRIPTION] = str(tool.description)
                elif hasattr(tool, "__doc__") and tool.__doc__:
                    # Fallback to docstring if no description attribute
                    attributes[ToolAttributes.TOOL_DESCRIPTION] = str(tool.__doc__).strip()
            else:
                # Multiple tools - use indexed format
                for i, tool in enumerate(agent.tools):
                    tool_name = None
                    if hasattr(tool, "name"):
                        tool_name = str(tool.name)
                        attributes[f"tool.{i}.name"] = tool_name
                    elif hasattr(tool, "__name__"):
                        tool_name = str(tool.__name__)
                        attributes[f"tool.{i}.name"] = tool_name
                    elif callable(tool):
                        tool_name = getattr(tool, "__name__", "unknown_tool")
                        attributes[f"tool.{i}.name"] = tool_name

                    if tool_name:
                        tool_names.append(tool_name)

                    if hasattr(tool, "description") and tool.description:
                        attributes[f"tool.{i}.description"] = str(tool.description)
                    elif hasattr(tool, "__doc__") and tool.__doc__:
                        # Fallback to docstring if no description attribute
                        attributes[f"tool.{i}.description"] = str(tool.__doc__).strip()

            # Set the AGENT_TOOLS attribute with all tool names
            if tool_names:
                attributes[AgentAttributes.AGENT_TOOLS] = json.dumps(tool_names)

        if hasattr(agent, "knowledge") and agent.knowledge:
            knowledge_type = type(agent.knowledge).__name__
            attributes["agent.knowledge_type"] = knowledge_type

        if hasattr(agent, "storage") and agent.storage:
            storage_type = type(agent.storage).__name__
            attributes["agent.storage_type"] = storage_type

        # Session information
        if hasattr(agent, "session_id") and agent.session_id:
            session_id = str(agent.session_id)
            attributes["agent.session_id"] = session_id

        if hasattr(agent, "user_id") and agent.user_id:
            user_id = str(agent.user_id)
            attributes["agent.user_id"] = user_id

        # Output key if present
        if hasattr(agent, "output_key") and agent.output_key:
            attributes["agent.output_key"] = str(agent.output_key)

    # Extract run input information
    if args and len(args) >= 2:
        message = args[1]  # The message argument
        if message:
            message_str = str(message)
            attributes["agent.input"] = message_str
            # AgentOps entity input
            attributes[SpanAttributes.AGENTOPS_ENTITY_INPUT] = message_str

    # Extract kwargs information
    if kwargs:
        if kwargs.get("stream") is not None:
            attributes[SpanAttributes.LLM_REQUEST_STREAMING] = str(kwargs["stream"])

        if kwargs.get("session_id"):
            attributes["agent.run_session_id"] = str(kwargs["session_id"])

        if kwargs.get("user_id"):
            attributes["agent.run_user_id"] = str(kwargs["user_id"])

    # Extract return value information
    if return_value:
        if hasattr(return_value, "run_id") and return_value.run_id:
            run_id = str(return_value.run_id)
            attributes["agent.run_id"] = run_id

        if hasattr(return_value, "content") and return_value.content:
            content = str(return_value.content)
            attributes["agent.output"] = content

        if hasattr(return_value, "event") and return_value.event:
            event = str(return_value.event)
            attributes["agent.event"] = event

        # Tool executions from the response
        if hasattr(return_value, "tools") and return_value.tools:
            # Track the number of tool executions
            attributes["agent.tool_executions_count"] = str(len(return_value.tools))

            for i, tool_exec in enumerate(return_value.tools):  # No limit - show all tools
                if hasattr(tool_exec, "tool_name") and tool_exec.tool_name:
                    attributes[f"tool.{i}.name"] = str(tool_exec.tool_name)

                if hasattr(tool_exec, "tool_args") and tool_exec.tool_args:
                    try:
                        args_str = json.dumps(tool_exec.tool_args)
                        attributes[f"tool.{i}.parameters"] = args_str
                    except:
                        attributes[f"tool.{i}.parameters"] = str(tool_exec.tool_args)

                if hasattr(tool_exec, "result") and tool_exec.result:
                    result_str = str(tool_exec.result)
                    attributes[f"tool.{i}.result"] = result_str

                if hasattr(tool_exec, "tool_call_error") and tool_exec.tool_call_error:
                    attributes[f"tool.{i}.error"] = str(tool_exec.tool_call_error)

                attributes[f"tool.{i}.status"] = "success"  # Default to success

    # Add display name for better UI visualization
    if agent_name:
        # Check if we have parent team info
        parent_team = attributes.get("agent.parent_team")
        if parent_team:
            attributes["agent.display_name"] = f"{agent_name} (Agent under {parent_team})"
        else:
            attributes["agent.display_name"] = f"{agent_name}"

    return attributes
