"""Agno Model response attributes handler."""

from typing import Optional, Tuple, Dict, Any

from agentops.instrumentation.common.attributes import AttributeMap
from agentops.semconv import SpanAttributes
from agentops.semconv.span_kinds import SpanKind as AgentOpsSpanKind


def get_model_response_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract span attributes for Model.response method calls.

    Args:
        args: Positional arguments passed to the Model.response method
        kwargs: Keyword arguments passed to the Model.response method
        return_value: The return value from the Model.response method

    Returns:
        A dictionary of span attributes to be set on the LLM span
    """
    attributes: AttributeMap = {}

    # Base attributes
    attributes[SpanAttributes.AGENTOPS_SPAN_KIND] = AgentOpsSpanKind.LLM_CALL
    attributes[SpanAttributes.LLM_SYSTEM] = "agno"

    print(f"[DEBUG] get_model_response_attributes called")

    # Process input arguments
    if kwargs:
        # Extract messages from kwargs
        messages = kwargs.get('messages')
        if messages:
            for i, msg in enumerate(messages):
                if isinstance(msg, dict):
                    if 'role' in msg:
                        attributes[f'gen_ai.prompt.{i}.role'] = msg['role']
                    if 'content' in msg:
                        content = msg['content']
                        if len(str(content)) > 1000:
                            content = str(content)[:997] + "..."
                        attributes[f'gen_ai.prompt.{i}.content'] = str(content)
                elif hasattr(msg, 'role') and hasattr(msg, 'content'):
                    attributes[f'gen_ai.prompt.{i}.role'] = msg.role
                    content = msg.content
                    if len(str(content)) > 1000:
                        content = str(content)[:997] + "..."
                    attributes[f'gen_ai.prompt.{i}.content'] = str(content)

        # Extract response format
        if kwargs.get('response_format'):
            attributes['agno.model.response_format'] = str(kwargs['response_format'])
        
        # Extract tools information
        tools = kwargs.get('tools')
        if tools:
            attributes['agno.model.tools_count'] = str(len(tools))
            for i, tool in enumerate(tools):
                if hasattr(tool, 'name'):
                    attributes[f'agno.model.tools.{i}.name'] = tool.name
                if hasattr(tool, 'description'):
                    description = tool.description
                    if len(str(description)) > 200:
                        description = str(description)[:197] + "..."
                    attributes[f'agno.model.tools.{i}.description'] = str(description)

        # Extract functions information  
        functions = kwargs.get('functions')
        if functions:
            attributes['agno.model.functions_count'] = str(len(functions))
            for i, func in enumerate(functions):
                if hasattr(func, 'name'):
                    attributes[f'agno.model.functions.{i}.name'] = func.name

        # Extract tool choice
        if kwargs.get('tool_choice'):
            attributes['agno.model.tool_choice'] = str(kwargs['tool_choice'])

        # Extract tool call limit
        if kwargs.get('tool_call_limit'):
            attributes['agno.model.tool_call_limit'] = str(kwargs['tool_call_limit'])

    # Process positional arguments (first arg is typically messages)
    if args and args[0] and not kwargs.get('messages'):
        messages = args[0]
        if isinstance(messages, list):
            for i, msg in enumerate(messages):
                if isinstance(msg, dict):
                    if 'role' in msg:
                        attributes[f'gen_ai.prompt.{i}.role'] = msg['role']
                    if 'content' in msg:
                        content = msg['content']
                        if len(str(content)) > 1000:
                            content = str(content)[:997] + "..."
                        attributes[f'gen_ai.prompt.{i}.content'] = str(content)

    # Process return value
    if return_value:
        # Set completion content
        if hasattr(return_value, 'content'):
            content = return_value.content
            if len(str(content)) > 1000:
                content = str(content)[:997] + "..."
            attributes['gen_ai.completion.0.content'] = str(content)
            attributes['gen_ai.completion.0.role'] = 'assistant'
        
        # Set usage metrics - Enhanced to capture all token types
        if hasattr(return_value, 'usage'):
            usage = return_value.usage
            if hasattr(usage, 'prompt_tokens'):
                attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = usage.prompt_tokens
            if hasattr(usage, 'completion_tokens'):
                attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = usage.completion_tokens
            if hasattr(usage, 'total_tokens'):
                attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = usage.total_tokens
            if hasattr(usage, 'reasoning_tokens'):
                attributes[SpanAttributes.LLM_USAGE_REASONING_TOKENS] = usage.reasoning_tokens
            if hasattr(usage, 'cached_tokens'):
                attributes[SpanAttributes.LLM_USAGE_CACHE_READ_INPUT_TOKENS] = usage.cached_tokens
            if hasattr(usage, 'cache_creation_input_tokens'):
                attributes[SpanAttributes.LLM_USAGE_CACHE_CREATION_INPUT_TOKENS] = usage.cache_creation_input_tokens

        # Set response usage if available 
        if hasattr(return_value, 'response_usage') and return_value.response_usage:
            response_usage = return_value.response_usage
            if hasattr(response_usage, 'prompt_tokens'):
                attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = response_usage.prompt_tokens
            if hasattr(response_usage, 'completion_tokens'):
                attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = response_usage.completion_tokens
            if hasattr(response_usage, 'total_tokens'):
                attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = response_usage.total_tokens

        # Set finish reason
        if hasattr(return_value, 'finish_reason'):
            attributes[SpanAttributes.LLM_RESPONSE_FINISH_REASON] = return_value.finish_reason

        # Set response ID
        if hasattr(return_value, 'id'):
            attributes[SpanAttributes.LLM_RESPONSE_ID] = str(return_value.id)

        # Set tool calls if present
        if hasattr(return_value, 'tool_calls') and return_value.tool_calls:
            for i, tool_call in enumerate(return_value.tool_calls):
                if hasattr(tool_call, 'function'):
                    function = tool_call.function
                    if hasattr(function, 'name'):
                        attributes[f'agno.model.response.tool_calls.{i}.name'] = function.name
                    if hasattr(function, 'arguments'):
                        args_str = str(function.arguments)
                        if len(args_str) > 500:
                            args_str = args_str[:497] + "..."
                        attributes[f'agno.model.response.tool_calls.{i}.arguments'] = args_str

        # Set raw response for debugging
        if hasattr(return_value, 'raw'):
            raw_response = str(return_value.raw)
            if len(raw_response) > 2000:
                raw_response = raw_response[:1997] + "..."
            attributes['agno.model.raw_response'] = raw_response

    return attributes


def get_session_metrics_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract span attributes from Agent._set_session_metrics method calls.

    This captures comprehensive session metrics AND model request/response data.

    Args:
        args: Positional arguments passed to the _set_session_metrics method
        kwargs: Keyword arguments passed to the _set_session_metrics method
        return_value: The return value from the _set_session_metrics method

    Returns:
        A dictionary of span attributes to be set on the metrics span
    """
    attributes: AttributeMap = {}

    # Base attributes
    attributes[SpanAttributes.AGENTOPS_SPAN_KIND] = AgentOpsSpanKind.AGENT
    attributes[SpanAttributes.LLM_SYSTEM] = "agno"
    
    print(f"[DEBUG] get_session_metrics_attributes called")
    print(f"[DEBUG] args: {args}")
    print(f"[DEBUG] kwargs: {kwargs}")
    print(f"[DEBUG] return_value: {return_value}")
    
    # The agent instance is the wrapped instance, args[0] is RunMessages
    # We need to access the agent through the call stack or extract data from RunMessages
    if args and len(args) > 0:
        run_messages = args[0]
        print(f"[DEBUG] run_messages type: {type(run_messages)}")
        
        # === EXTRACT DATA FROM RUNMESSAGES ===
        if hasattr(run_messages, 'messages') and run_messages.messages:
            messages = run_messages.messages
            print(f"[DEBUG] Found {len(messages)} messages")
            
            total_prompt_tokens = 0
            total_completion_tokens = 0
            total_tokens = 0
            total_time = 0
            
            prompt_count = 0
            completion_count = 0
            
            # Process each message
            for i, msg in enumerate(messages):
                print(f"[DEBUG] Message {i}: role={getattr(msg, 'role', 'unknown')}")
                
                # Extract message content for prompts/completions
                if hasattr(msg, 'role') and hasattr(msg, 'content'):
                    # Only set content if it's not None/empty
                    if msg.content is not None and str(msg.content).strip() != "" and str(msg.content) != "None":
                        content = str(msg.content)
                        if len(content) > 1000:
                            content = content[:997] + "..."
                        
                        if msg.role == 'user':
                            attributes[f'gen_ai.prompt.{prompt_count}.role'] = 'user'
                            attributes[f'gen_ai.prompt.{prompt_count}.content'] = content
                            prompt_count += 1
                        elif msg.role == 'assistant':
                            attributes[f'gen_ai.completion.{completion_count}.role'] = 'assistant'
                            attributes[f'gen_ai.completion.{completion_count}.content'] = content
                            completion_count += 1
                    else:
                        # For messages with None content, still set the role but skip content
                        if msg.role == 'user':
                            attributes[f'gen_ai.prompt.{prompt_count}.role'] = 'user'
                            prompt_count += 1
                        elif msg.role == 'assistant':
                            attributes[f'gen_ai.completion.{completion_count}.role'] = 'assistant'
                            completion_count += 1
                
                # Extract token metrics from message
                if hasattr(msg, 'metrics') and msg.metrics:
                    metrics = msg.metrics
                    print(f"[DEBUG] Message {i} metrics: {metrics}")
                    
                    # Handle different token metric patterns
                    if hasattr(metrics, 'prompt_tokens') and metrics.prompt_tokens > 0:
                        total_prompt_tokens += metrics.prompt_tokens
                    if hasattr(metrics, 'completion_tokens') and metrics.completion_tokens > 0:
                        total_completion_tokens += metrics.completion_tokens
                    if hasattr(metrics, 'total_tokens') and metrics.total_tokens > 0:
                        total_tokens += metrics.total_tokens
                    # For messages that only have output_tokens (like Anthropic)
                    if hasattr(metrics, 'output_tokens') and metrics.output_tokens > 0:
                        total_completion_tokens += metrics.output_tokens
                    if hasattr(metrics, 'time') and metrics.time:
                        total_time += metrics.time
            
            # Set aggregated token usage
            if total_prompt_tokens > 0:
                attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = total_prompt_tokens
                attributes['agno.metrics.prompt_tokens'] = total_prompt_tokens
            if total_completion_tokens > 0:
                attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = total_completion_tokens
                attributes['agno.metrics.completion_tokens'] = total_completion_tokens
            if total_tokens > 0:
                attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = total_tokens
                
                # Handle case where we have total but no breakdown (common with Anthropic)
                if total_prompt_tokens == 0 and total_completion_tokens == 0:
                    # We'll try to get the breakdown from session_metrics later
                    print(f"[DEBUG] Total tokens ({total_tokens}) available but no breakdown - will try session_metrics")
                elif total_prompt_tokens > 0 or total_completion_tokens > 0:
                    # Ensure totals are consistent
                    calculated_total = total_prompt_tokens + total_completion_tokens
                    if calculated_total != total_tokens:
                        print(f"[DEBUG] Token mismatch: calculated={calculated_total}, reported={total_tokens}")
                        # Use the more reliable total
                        attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = max(total_tokens, calculated_total)
                        
            if total_time > 0:
                attributes['agno.metrics.total_time'] = total_time
                
            print(f"[DEBUG] Aggregated tokens: prompt={total_prompt_tokens}, completion={total_completion_tokens}, total={total_tokens}, time={total_time}")

        # Extract user message info
        if hasattr(run_messages, 'user_message') and run_messages.user_message:
            user_msg = run_messages.user_message
            if hasattr(user_msg, 'content'):
                content = str(user_msg.content)
                if len(content) > 1000:
                    content = content[:997] + "..."
                attributes['agno.metrics.user_input'] = content

    # Try to get agent instance from the call stack for additional data
    import inspect
    try:
        for frame in inspect.stack():
            frame_locals = frame.frame.f_locals
            # Look for agent instance in the call stack
            for var_name, var_value in frame_locals.items():
                if (hasattr(var_value, 'session_metrics') and 
                    hasattr(var_value, 'run') and 
                    var_name in ['self', 'agent', 'instance']):
                    agent_instance = var_value
                    print(f"[DEBUG] Found agent instance in call stack: {type(agent_instance)}")
                    
                    # === MODEL INFO FROM AGENT ===
                    if hasattr(agent_instance, 'model') and agent_instance.model:
                        model = agent_instance.model
                        if hasattr(model, 'id'):
                            attributes[SpanAttributes.LLM_REQUEST_MODEL] = str(model.id)
                            attributes[SpanAttributes.LLM_RESPONSE_MODEL] = str(model.id)
                        if hasattr(model, 'provider'):
                            attributes['agno.model.provider'] = str(model.provider)

                    # === TOOLS INFO FROM AGENT ===
                    if hasattr(agent_instance, 'tools') and agent_instance.tools:
                        tools = agent_instance.tools
                        attributes['agno.model.tools_count'] = str(len(tools))
                        for i, tool in enumerate(tools):
                            if hasattr(tool, 'name'):
                                attributes[f'agno.model.tools.{i}.name'] = tool.name
                    
                    # === SESSION METRICS FROM AGENT (if available) ===
                    if hasattr(agent_instance, 'session_metrics') and agent_instance.session_metrics:
                        session_metrics = agent_instance.session_metrics
                        print(f"[DEBUG] Found session_metrics on agent: {session_metrics}")
                        
                        # Use session metrics for more accurate token counts
                        session_prompt_tokens = getattr(session_metrics, 'prompt_tokens', 0)
                        session_completion_tokens = getattr(session_metrics, 'completion_tokens', 0)
                        session_output_tokens = getattr(session_metrics, 'output_tokens', 0)
                        session_total_tokens = getattr(session_metrics, 'total_tokens', 0)
                        
                        # For Anthropic, output_tokens represents completion tokens
                        if session_output_tokens > 0 and session_completion_tokens == 0:
                            session_completion_tokens = session_output_tokens
                            
                        # Only override if session metrics provide better breakdown
                        if session_total_tokens > 0:
                            attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = session_total_tokens
                            
                            # Set breakdown if available
                            if session_prompt_tokens > 0:
                                attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = session_prompt_tokens
                                attributes['agno.metrics.prompt_tokens'] = session_prompt_tokens
                            if session_completion_tokens > 0:
                                attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = session_completion_tokens
                                attributes['agno.metrics.completion_tokens'] = session_completion_tokens
                                
                            # If we have total but still no breakdown, estimate it
                            if session_prompt_tokens == 0 and session_completion_tokens > 0:
                                # All tokens are completion tokens (common for generative responses)
                                print(f"[DEBUG] Using all {session_total_tokens} tokens as completion tokens")
                            elif session_prompt_tokens > 0 and session_completion_tokens == 0:
                                # All tokens are prompt tokens (rare case)
                                print(f"[DEBUG] Using all {session_total_tokens} tokens as prompt tokens")

                        if hasattr(session_metrics, 'time') and session_metrics.time:
                            attributes['agno.metrics.total_time'] = session_metrics.time

                    break
    except Exception as e:
        print(f"[DEBUG] Error accessing call stack: {e}")

    print(f"[DEBUG] Final attributes keys: {list(attributes.keys())}")
    return attributes 