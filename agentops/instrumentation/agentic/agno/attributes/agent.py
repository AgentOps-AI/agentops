"""Agno Agent run attributes handler."""

from typing import Optional, Tuple, Dict, Any

from agentops.instrumentation.common.attributes import AttributeMap
from agentops.semconv import SpanAttributes, WorkflowAttributes, AgentAttributes, ToolAttributes
from agentops.semconv.span_kinds import SpanKind as AgentOpsSpanKind


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
    attributes[SpanAttributes.AGENTOPS_SPAN_KIND] = AgentOpsSpanKind.WORKFLOW
    attributes[SpanAttributes.LLM_SYSTEM] = "agno"
    attributes[SpanAttributes.LLM_REQUEST_STREAMING] = "False"

    # AgentOps entity attributes (matching CrewAI pattern)
    attributes[SpanAttributes.AGENTOPS_ENTITY_NAME] = "Agent"

    # Extract agent information from args[0] (self)
    if args and len(args) >= 1:
        agent = args[0]

        # Core agent identification using AgentAttributes
        if hasattr(agent, "agent_id") and agent.agent_id:
            agent_id = str(agent.agent_id)
            attributes[AgentAttributes.AGENT_ID] = agent_id
            attributes["agno.agent.id"] = agent_id

        if hasattr(agent, "name") and agent.name:
            agent_name = str(agent.name)
            attributes[AgentAttributes.AGENT_NAME] = agent_name
            attributes["agno.agent.name"] = agent_name

        if hasattr(agent, "role") and agent.role:
            agent_role = str(agent.role)
            attributes[AgentAttributes.AGENT_ROLE] = agent_role
            attributes["agno.agent.role"] = agent_role

        # Check if agent is part of a team
        if hasattr(agent, "_team") and agent._team:
            team = agent._team
            if hasattr(team, "name") and team.name:
                attributes["agno.agent.parent_team"] = str(team.name)
                attributes["agno.agent.parent_team_display"] = f"Under {team.name}"
            if hasattr(team, "team_id") and team.team_id:
                attributes["agno.agent.parent_team_id"] = str(team.team_id)

        # Model information using AgentAttributes
        if hasattr(agent, "model") and agent.model:
            model = agent.model
            if hasattr(model, "id"):
                model_id = str(model.id)
                attributes[AgentAttributes.AGENT_MODELS] = model_id
                attributes["agno.agent.model_id"] = model_id
                attributes[SpanAttributes.LLM_RESPONSE_MODEL] = model_id

            if hasattr(model, "provider"):
                model_provider = str(model.provider)
                attributes["agno.agent.model_provider"] = model_provider
                attributes[SpanAttributes.LLM_REQUEST_MODEL] = model_id if hasattr(model, "id") else "unknown"

        # Agent configuration details
        agent_config = {}

        if hasattr(agent, "description") and agent.description:
            agent_config["description"] = str(agent.description)[:500]  # Limit length

        if hasattr(agent, "goal") and agent.goal:
            agent_config["goal"] = str(agent.goal)[:500]  # Limit length

        if hasattr(agent, "instructions") and agent.instructions:
            if isinstance(agent.instructions, list):
                agent_config["instructions"] = " | ".join(str(i) for i in agent.instructions[:3])  # First 3
            else:
                agent_config["instructions"] = str(agent.instructions)[:500]

        if hasattr(agent, "expected_output") and agent.expected_output:
            agent_config["expected_output"] = str(agent.expected_output)[:300]

        if hasattr(agent, "markdown"):
            agent_config["markdown"] = str(agent.markdown)

        if hasattr(agent, "reasoning"):
            agent_config["reasoning"] = str(agent.reasoning)

        if hasattr(agent, "stream"):
            agent_config["stream"] = str(agent.stream)

        if hasattr(agent, "retries"):
            agent_config["max_retry_limit"] = str(agent.retries)

        if hasattr(agent, "response_model") and agent.response_model:
            agent_config[SpanAttributes.LLM_RESPONSE_MODEL] = str(agent.response_model.__name__)

        if hasattr(agent, "show_tool_calls"):
            agent_config["show_tool_calls"] = str(agent.show_tool_calls)

        if hasattr(agent, "tool_call_limit") and agent.tool_call_limit:
            agent_config["tool_call_limit"] = str(agent.tool_call_limit)

        # Add agent config to attributes
        for key, value in agent_config.items():
            attributes[f"agno.agent.{key}"] = value

        # Tools information
        if hasattr(agent, "tools") and agent.tools:
            tools_info = []
            tool_names = []

            for tool in agent.tools:
                tool_dict = {}

                if hasattr(tool, "name"):
                    tool_name = str(tool.name)
                    tool_dict["name"] = tool_name
                    tool_names.append(tool_name)
                elif hasattr(tool, "__name__"):
                    tool_name = str(tool.__name__)
                    tool_dict["name"] = tool_name
                    tool_names.append(tool_name)
                elif callable(tool):
                    tool_name = getattr(tool, "__name__", "unknown_tool")
                    tool_dict["name"] = tool_name
                    tool_names.append(tool_name)

                if hasattr(tool, "description"):
                    description = str(tool.description)
                    if len(description) > 200:
                        description = description[:197] + "..."
                    tool_dict["description"] = description

                if tool_dict:  # Only add if we have some info
                    tools_info.append(tool_dict)

            # Set tool attributes
            if tool_names:
                attributes["agno.agent.tools_count"] = str(len(tool_names))

            if tools_info:
                # Instead of storing as JSON blob, set individual tool attributes
                for i, tool in enumerate(tools_info):
                    prefix = f"agent.tool.{i}"
                    if "name" in tool:
                        attributes[f"{prefix}.{ToolAttributes.TOOL_NAME}"] = tool["name"]
                    if "description" in tool:
                        attributes[f"{prefix}.{ToolAttributes.TOOL_DESCRIPTION}"] = tool["description"]

        # Memory and knowledge information
        if hasattr(agent, "memory") and agent.memory:
            memory_type = type(agent.memory).__name__
            attributes["agno.agent.memory_type"] = memory_type

        if hasattr(agent, "knowledge") and agent.knowledge:
            knowledge_type = type(agent.knowledge).__name__
            attributes["agno.agent.knowledge_type"] = knowledge_type

        if hasattr(agent, "storage") and agent.storage:
            storage_type = type(agent.storage).__name__
            attributes["agno.agent.storage_type"] = storage_type

        # Session information
        if hasattr(agent, "session_id") and agent.session_id:
            session_id = str(agent.session_id)
            attributes["agno.agent.session_id"] = session_id

        if hasattr(agent, "user_id") and agent.user_id:
            user_id = str(agent.user_id)
            attributes["agno.agent.user_id"] = user_id

    # Extract run input information
    if args and len(args) >= 2:
        message = args[1]  # The message argument
        if message:
            message_str = str(message)
            if len(message_str) > 500:
                message_str = message_str[:497] + "..."
            attributes[WorkflowAttributes.WORKFLOW_INPUT] = message_str
            attributes["agno.agent.input"] = message_str
            # AgentOps entity input (matching CrewAI pattern)
            attributes[SpanAttributes.AGENTOPS_ENTITY_INPUT] = message_str

    # Extract kwargs information
    if kwargs:
        if kwargs.get("stream") is not None:
            attributes[SpanAttributes.LLM_REQUEST_STREAMING] = str(kwargs["stream"])

        if kwargs.get("session_id"):
            attributes["agno.agent.run_session_id"] = str(kwargs["session_id"])

        if kwargs.get("user_id"):
            attributes["agno.agent.run_user_id"] = str(kwargs["user_id"])

    # Extract return value information
    if return_value:
        if hasattr(return_value, "run_id") and return_value.run_id:
            run_id = str(return_value.run_id)
            attributes["agno.agent.run_id"] = run_id

        if hasattr(return_value, "session_id") and return_value.session_id:
            session_id = str(return_value.session_id)
            attributes["agno.agent.response_session_id"] = session_id

        if hasattr(return_value, "agent_id") and return_value.agent_id:
            agent_id = str(return_value.agent_id)
            attributes["agno.agent.response_agent_id"] = agent_id

        if hasattr(return_value, "content") and return_value.content:
            content = str(return_value.content)
            if len(content) > 500:
                content = content[:497] + "..."
            attributes[WorkflowAttributes.WORKFLOW_OUTPUT] = content
            attributes["agno.agent.output"] = content

        if hasattr(return_value, "event") and return_value.event:
            event = str(return_value.event)
            attributes["agno.agent.event"] = event

        # Tool executions from the response
        if hasattr(return_value, "tools") and return_value.tools:
            tool_executions = []
            for tool_exec in return_value.tools:
                tool_exec_dict = {}

                if hasattr(tool_exec, "tool_name") and tool_exec.tool_name:
                    tool_exec_dict["name"] = str(tool_exec.tool_name)

                if hasattr(tool_exec, "tool_args") and tool_exec.tool_args:
                    try:
                        import json

                        args_str = json.dumps(tool_exec.tool_args)
                        if len(args_str) > 200:
                            args_str = args_str[:197] + "..."
                        tool_exec_dict["parameters"] = args_str
                    except:
                        tool_exec_dict["parameters"] = str(tool_exec.tool_args)

                if hasattr(tool_exec, "result") and tool_exec.result:
                    result_str = str(tool_exec.result)
                    if len(result_str) > 200:
                        result_str = result_str[:197] + "..."
                    tool_exec_dict["result"] = result_str

                if hasattr(tool_exec, "tool_call_error") and tool_exec.tool_call_error:
                    tool_exec_dict["error"] = str(tool_exec.tool_call_error)

                tool_exec_dict["status"] = "success"  # Default to success

                if tool_exec_dict:
                    tool_executions.append(tool_exec_dict)

            if tool_executions:
                # Add tool executions (limit to first 3)
                limited_executions = tool_executions[:3]
                for i, tool_exec in enumerate(limited_executions):
                    for key, value in tool_exec.items():
                        attributes[f"agno.agent.tool_execution.{i}.{key}"] = value

        # Workflow type
        attributes[WorkflowAttributes.WORKFLOW_TYPE] = "agent_run"

    # Add display name for better UI visualization
    if agent_name:
        # Check if we have parent team info
        parent_team = attributes.get("agno.agent.parent_team")
        if parent_team:
            attributes["agno.agent.display_name"] = f"{agent_name} (Agent under {parent_team})"
        else:
            attributes["agno.agent.display_name"] = f"{agent_name} (Agent)"

    return attributes
