"""Agno Team run attributes handler."""

from typing import Optional, Tuple, Dict, Any
import json
from agentops.instrumentation.common.attributes import AttributeMap
from agentops.semconv import SpanAttributes, WorkflowAttributes
from agentops.semconv.span_kinds import SpanKind as AgentOpsSpanKind


def get_team_run_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract span attributes for Team method calls (both internal and public).

    Args:
        args: Positional arguments passed to the Team method
        kwargs: Keyword arguments passed to the Team method
        return_value: The return value from the Team method

    Returns:
        A dictionary of span attributes to be set on the workflow span
    """
    attributes: AttributeMap = {}

    # Base attributes
    attributes[SpanAttributes.AGENTOPS_SPAN_KIND] = AgentOpsSpanKind.WORKFLOW
    attributes[SpanAttributes.LLM_SYSTEM] = "agno"
    attributes[WorkflowAttributes.WORKFLOW_TYPE] = "team_run"

    # Extract team information from instance
    if args and len(args) > 0:
        team = args[0]  # self (Team instance)

        # Team identification
        if hasattr(team, "name") and team.name:
            attributes["team.name"] = str(team.name)
            attributes["team.display_name"] = f"{team.name} (Team)"

        if hasattr(team, "team_id") and team.team_id:
            attributes["team.team_id"] = str(team.team_id)

        if hasattr(team, "mode") and team.mode:
            attributes["team.mode"] = str(team.mode)

        if hasattr(team, "members") and team.members:
            attributes["team.members_count"] = str(len(team.members))

            # Add detailed member information
            member_agents = []
            for i, member in enumerate(team.members):
                member_info = {}
                if hasattr(member, "name") and member.name:
                    member_info["name"] = str(member.name)
                if hasattr(member, "agent_id") and member.agent_id:
                    member_info["id"] = str(member.agent_id)
                if hasattr(member, "role") and member.role:
                    member_info["role"] = str(member.role)
                if hasattr(member, "model") and member.model:
                    if hasattr(member.model, "id"):
                        member_info["model"] = str(member.model.id)

                # Add member info to list
                if member_info:
                    member_agents.append(member_info)

                    # Also add individual member attributes
                    for key, value in member_info.items():
                        attributes[f"team.member.{i}.{key}"] = value

            # Add aggregated member list
            if member_agents:
                try:
                    attributes["team.members"] = json.dumps(member_agents)
                    # Also add a simple list of member names
                    member_names = [m.get("name", "Unknown") for m in member_agents]
                    attributes["team.member_names"] = ", ".join(member_names)
                except:
                    attributes["team.members"] = str(member_agents)

    # Process input arguments - handle both internal and public method signatures
    if args and len(args) >= 2:
        input_arg = args[1]

        # Check if it's internal method (has run_messages) or public method (direct message)
        if hasattr(input_arg, "messages"):
            # Internal method: args[1] is run_messages
            run_messages = input_arg
            # Get the user message for workflow input
            user_messages = [msg for msg in run_messages.messages if hasattr(msg, "role") and msg.role == "user"]
            if user_messages:
                last_user_msg = user_messages[-1]
                if hasattr(last_user_msg, "content"):
                    attributes[WorkflowAttributes.WORKFLOW_INPUT] = str(last_user_msg.content)
                    attributes[WorkflowAttributes.WORKFLOW_INPUT_TYPE] = "message"
            # Count total messages
            attributes["team.messages_count"] = str(len(run_messages.messages))
        else:
            # Public method: args[1] is the message directly
            message = input_arg
            if message is not None:
                if isinstance(message, str):
                    message_content = message
                elif hasattr(message, "content"):
                    message_content = str(message.content)
                elif hasattr(message, "get_content_string"):
                    message_content = message.get_content_string()
                else:
                    message_content = str(message)

                attributes[WorkflowAttributes.WORKFLOW_INPUT] = message_content
                attributes[WorkflowAttributes.WORKFLOW_INPUT_TYPE] = "message"

    # Process keyword arguments
    if kwargs:
        if kwargs.get("user_id"):
            attributes[SpanAttributes.LLM_USER] = kwargs["user_id"]

        if kwargs.get("session_id"):
            attributes["team.session_id"] = kwargs["session_id"]

        if kwargs.get("response_format"):
            attributes["team.response_format"] = str(type(kwargs["response_format"]).__name__)

        if kwargs.get("stream"):
            attributes["team.streaming"] = str(kwargs["stream"])

        if kwargs.get("stream_intermediate_steps"):
            attributes["team.stream_intermediate_steps"] = str(kwargs["stream_intermediate_steps"])

        if kwargs.get("retries"):
            attributes["team.retries"] = str(kwargs["retries"])

        # Media attachments
        if kwargs.get("audio"):
            attributes["team.has_audio"] = "true"
        if kwargs.get("images"):
            attributes["team.has_images"] = "true"
        if kwargs.get("videos"):
            attributes["team.has_videos"] = "true"
        if kwargs.get("files"):
            attributes["team.has_files"] = "true"

        if kwargs.get("knowledge_filters"):
            attributes["team.has_knowledge_filters"] = "true"

    # Process return value (TeamRunResponse or Iterator)
    if return_value:
        # Handle both single response and iterator
        if hasattr(return_value, "__iter__") and not isinstance(return_value, str):
            # It's an iterator for streaming
            attributes[WorkflowAttributes.WORKFLOW_OUTPUT_TYPE] = "team_run_response_stream"
            attributes["team.is_streaming"] = "true"
        else:
            # Non-streaming response
            if hasattr(return_value, "content"):
                # It's a TeamRunResponse with content
                content = str(return_value.content)
                attributes[WorkflowAttributes.WORKFLOW_OUTPUT] = content
                attributes[WorkflowAttributes.WORKFLOW_OUTPUT_TYPE] = "team_run_response"
            else:
                # Unknown return type or response without content
                output = str(return_value)
                attributes[WorkflowAttributes.WORKFLOW_OUTPUT] = output
                attributes[WorkflowAttributes.WORKFLOW_OUTPUT_TYPE] = type(return_value).__name__

        # Set additional team response attributes (for both streaming and non-streaming)
        if hasattr(return_value, "run_id"):
            attributes["team.run_id"] = str(return_value.run_id)

        if hasattr(return_value, "session_id"):
            attributes["team.response_session_id"] = str(return_value.session_id)

        if hasattr(return_value, "team_id"):
            attributes["team.response_team_id"] = str(return_value.team_id)

        if hasattr(return_value, "model"):
            attributes[SpanAttributes.LLM_RESPONSE_MODEL] = str(return_value.model)

        if hasattr(return_value, "model_provider"):
            attributes["team.model_provider"] = str(return_value.model_provider)

        if hasattr(return_value, "event"):
            attributes["team.event"] = str(return_value.event)

        # Team-specific attributes
        if hasattr(return_value, "content_type"):
            attributes["team.response_content_type"] = str(return_value.content_type)

    return attributes


# Keep the public function as an alias for backward compatibility
get_team_public_run_attributes = get_team_run_attributes
