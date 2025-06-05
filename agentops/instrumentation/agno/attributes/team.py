"""Agno Team run attributes handler."""

from typing import Optional, Tuple, Dict, Any

from agentops.instrumentation.common.attributes import AttributeMap
from agentops.semconv import SpanAttributes, WorkflowAttributes
from agentops.semconv.span_kinds import SpanKind as AgentOpsSpanKind


def get_team_run_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract span attributes for Team._run method calls.

    Args:
        args: Positional arguments passed to the Team._run method
        kwargs: Keyword arguments passed to the Team._run method
        return_value: The return value from the Team._run method

    Returns:
        A dictionary of span attributes to be set on the workflow span
    """
    attributes: AttributeMap = {}

    # Base attributes
    attributes[SpanAttributes.AGENTOPS_SPAN_KIND] = AgentOpsSpanKind.WORKFLOW
    attributes[SpanAttributes.LLM_SYSTEM] = "agno"
    attributes[WorkflowAttributes.WORKFLOW_TYPE] = "team_run"

    # Process input arguments from the run_messages parameter
    if args and len(args) >= 2:
        # args[0] is run_response, args[1] is run_messages
        run_messages = args[1]
        if hasattr(run_messages, 'messages') and run_messages.messages:
            # Get the user message for workflow input
            user_messages = [msg for msg in run_messages.messages if hasattr(msg, 'role') and msg.role == 'user']
            if user_messages:
                last_user_msg = user_messages[-1]
                if hasattr(last_user_msg, 'content'):
                    attributes[WorkflowAttributes.WORKFLOW_INPUT] = str(last_user_msg.content)
                    attributes[WorkflowAttributes.WORKFLOW_INPUT_TYPE] = "message"
            
            # Count total messages
            attributes['agno.team.messages_count'] = str(len(run_messages.messages))

    # Process keyword arguments
    if kwargs:
        if kwargs.get('user_id'):
            attributes[SpanAttributes.LLM_USER] = kwargs['user_id']
        
        if kwargs.get('session_id'):
            attributes['agno.team.session_id'] = kwargs['session_id']
            
        if kwargs.get('response_format'):
            attributes['agno.team.response_format'] = str(type(kwargs['response_format']).__name__)

    # Process return value (TeamRunResponse)
    if return_value:
        if hasattr(return_value, 'content'):
            content = str(return_value.content)
            # Truncate if too long
            if len(content) > 1000:
                content = content[:997] + "..."
            attributes[WorkflowAttributes.WORKFLOW_OUTPUT] = content
            attributes[WorkflowAttributes.WORKFLOW_OUTPUT_TYPE] = "team_run_response"
        else:
            output = str(return_value)
            if len(output) > 1000:
                output = output[:997] + "..."
            attributes[WorkflowAttributes.WORKFLOW_OUTPUT] = output
            attributes[WorkflowAttributes.WORKFLOW_OUTPUT_TYPE] = type(return_value).__name__
        
        # Set additional team response attributes
        if hasattr(return_value, 'run_id'):
            attributes['agno.team.run_id'] = str(return_value.run_id)
        
        if hasattr(return_value, 'session_id'):
            attributes['agno.team.response_session_id'] = str(return_value.session_id)
        
        if hasattr(return_value, 'team_id'):
            attributes['agno.team.response_team_id'] = str(return_value.team_id)
        
        if hasattr(return_value, 'model'):
            attributes[SpanAttributes.LLM_RESPONSE_MODEL] = str(return_value.model)
        
        if hasattr(return_value, 'model_provider'):
            attributes['agno.team.model_provider'] = str(return_value.model_provider)
        
        if hasattr(return_value, 'event'):
            attributes['agno.team.event'] = str(return_value.event)
            
        # Team-specific attributes
        if hasattr(return_value, 'content_type'):
            attributes['agno.team.response_content_type'] = str(return_value.content_type)

    return attributes


def get_team_public_run_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract span attributes for Team.run method calls (public API).

    Args:
        args: Positional arguments passed to the Team.run method (self, message, ...)
        kwargs: Keyword arguments passed to the Team.run method
        return_value: The return value from the Team.run method

    Returns:
        A dictionary of span attributes to be set on the workflow span
    """
    attributes: AttributeMap = {}

    # Base attributes
    attributes[SpanAttributes.AGENTOPS_SPAN_KIND] = AgentOpsSpanKind.WORKFLOW
    attributes[SpanAttributes.LLM_SYSTEM] = "agno"
    attributes[WorkflowAttributes.WORKFLOW_TYPE] = "team_run"

    # Process input arguments from Team.run() method
    if args and len(args) >= 2:
        # args[0] is self (Team instance), args[1] is message
        team_instance = args[0]
        message = args[1]
        
        # Extract team information
        if hasattr(team_instance, 'name') and team_instance.name:
            attributes['agno.team.name'] = str(team_instance.name)
            
        if hasattr(team_instance, 'team_id') and team_instance.team_id:
            attributes['agno.team.team_id'] = str(team_instance.team_id)
            
        if hasattr(team_instance, 'mode') and team_instance.mode:
            attributes['agno.team.mode'] = str(team_instance.mode)
            
        if hasattr(team_instance, 'members') and team_instance.members:
            attributes['agno.team.members_count'] = str(len(team_instance.members))
        
        # Extract workflow input from message
        if message is not None:
            if isinstance(message, str):
                message_content = message
            elif hasattr(message, 'content'):
                message_content = str(message.content)
            elif hasattr(message, 'get_content_string'):
                message_content = message.get_content_string()
            else:
                message_content = str(message)
            
            # Truncate if too long
            if len(message_content) > 1000:
                message_content = message_content[:997] + "..."
            attributes[WorkflowAttributes.WORKFLOW_INPUT] = message_content
            attributes[WorkflowAttributes.WORKFLOW_INPUT_TYPE] = "message"

    # Process keyword arguments
    if kwargs:
        if kwargs.get('user_id'):
            attributes[SpanAttributes.LLM_USER] = kwargs['user_id']
        
        if kwargs.get('session_id'):
            attributes['agno.team.session_id'] = kwargs['session_id']
            
        if kwargs.get('stream'):
            attributes['agno.team.streaming'] = str(kwargs['stream'])
            
        if kwargs.get('stream_intermediate_steps'):
            attributes['agno.team.stream_intermediate_steps'] = str(kwargs['stream_intermediate_steps'])
            
        if kwargs.get('retries'):
            attributes['agno.team.retries'] = str(kwargs['retries'])
            
        # Media attachments
        if kwargs.get('audio'):
            attributes['agno.team.has_audio'] = "true"
        if kwargs.get('images'):
            attributes['agno.team.has_images'] = "true"
        if kwargs.get('videos'):
            attributes['agno.team.has_videos'] = "true"
        if kwargs.get('files'):
            attributes['agno.team.has_files'] = "true"
            
        if kwargs.get('knowledge_filters'):
            attributes['agno.team.has_knowledge_filters'] = "true"

    # Process return value (TeamRunResponse or Iterator)
    if return_value:
        # Handle both single response and iterator
        if hasattr(return_value, '__iter__') and not isinstance(return_value, str):
            # It's an iterator for streaming
            attributes[WorkflowAttributes.WORKFLOW_OUTPUT_TYPE] = "team_run_response_stream"
            attributes['agno.team.is_streaming'] = "true"
        elif hasattr(return_value, 'content'):
            # It's a TeamRunResponse
            content = str(return_value.content)
            # Truncate if too long
            if len(content) > 1000:
                content = content[:997] + "..."
            attributes[WorkflowAttributes.WORKFLOW_OUTPUT] = content
            attributes[WorkflowAttributes.WORKFLOW_OUTPUT_TYPE] = "team_run_response"
            
            # Set additional team response attributes
            if hasattr(return_value, 'run_id'):
                attributes['agno.team.run_id'] = str(return_value.run_id)
            
            if hasattr(return_value, 'session_id'):
                attributes['agno.team.response_session_id'] = str(return_value.session_id)
            
            if hasattr(return_value, 'team_id'):
                attributes['agno.team.response_team_id'] = str(return_value.team_id)
            
            if hasattr(return_value, 'model'):
                attributes[SpanAttributes.LLM_RESPONSE_MODEL] = str(return_value.model)
            
            if hasattr(return_value, 'model_provider'):
                attributes['agno.team.model_provider'] = str(return_value.model_provider)
            
            if hasattr(return_value, 'event'):
                attributes['agno.team.event'] = str(return_value.event)
                
            # Team-specific attributes
            if hasattr(return_value, 'content_type'):
                attributes['agno.team.response_content_type'] = str(return_value.content_type)
        else:
            # Unknown return type
            output = str(return_value)
            if len(output) > 1000:
                output = output[:997] + "..."
            attributes[WorkflowAttributes.WORKFLOW_OUTPUT] = output
            attributes[WorkflowAttributes.WORKFLOW_OUTPUT_TYPE] = type(return_value).__name__

    return attributes 