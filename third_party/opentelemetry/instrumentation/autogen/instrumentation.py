import functools
import logging
import time
import asyncio
import json
from typing import Collection, Optional, Dict, Any

from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.metrics import Histogram, Meter, get_meter
from opentelemetry.trace import Span, SpanKind, Tracer, get_tracer
from wrapt import wrap_function_wrapper

from agentops.semconv import AgentOpsSpanKindValues, SpanAttributes
from .autogen_span_attributes import (
    AutoGenSpanAttributes, 
    extract_message_attributes, 
    extract_token_usage, 
    set_span_attribute
)
from .version import __version__

logger = logging.getLogger(__name__)

# Define constants for metrics
class Meters:
    LLM_TOKEN_USAGE = "autogen.llm.token_usage"
    LLM_OPERATION_DURATION = "autogen.operation.duration"


class AutoGenInstrumentor(BaseInstrumentor):
    """An instrumentor for AutoGen."""

    def instrumentation_dependencies(self) -> Collection[str]:
        return ["autogen"]

    def _instrument(self, **kwargs):
        """Instrument AutoGen."""
        tracer_provider = kwargs.get("tracer_provider")
        meter_provider = kwargs.get("meter_provider")
        
        tracer = get_tracer(__name__, __version__, tracer_provider)
        meter = get_meter(__name__, __version__, meter_provider)
        
        # Create metrics if enabled
        if is_metrics_enabled():
            token_histogram, duration_histogram = _create_metrics(meter)
        else:
            token_histogram, duration_histogram = None, None
        
        logger.info("Instrumenting AutoGen")
        
        # Keep generate_reply as it provides high-level message generation info
        try:
            # Message generation
            wrap_function_wrapper(
                "autogen.agentchat.conversable_agent", 
                "ConversableAgent.generate_reply", 
                wrap_generate_reply(tracer, token_histogram, duration_histogram)
            )
            logger.info("Instrumented ConversableAgent.generate_reply")
        except Exception as e:
            logger.warning(f"Failed to instrument ConversableAgent.generate_reply: {e}")
        
        # LLM API calls - Use generate_oai_reply instead of _generate_oai_reply
        try:
            wrap_function_wrapper(
                "autogen.agentchat.conversable_agent", 
                "ConversableAgent.generate_oai_reply", 
                wrap_generate_oai_reply(tracer, token_histogram, duration_histogram)
            )
            logger.info("Instrumented ConversableAgent.generate_oai_reply")
        except Exception as e:
            logger.warning(f"Failed to instrument ConversableAgent.generate_oai_reply: {e}")
        
        # Tool execution - Use execute_function instead of _call_function
        try:
            wrap_function_wrapper(
                "autogen.agentchat.conversable_agent", 
                "ConversableAgent.execute_function", 
                wrap_call_function(tracer, duration_histogram, token_histogram)
            )
            logger.info("Instrumented ConversableAgent.execute_function")
        except Exception as e:
            logger.warning(f"Failed to instrument ConversableAgent.execute_function: {e}")
        
        # Group chat - Check if GroupChat.run exists before instrumenting
        try:
            import autogen.agentchat.groupchat
            wrap_function_wrapper(
                "autogen.agentchat.groupchat", 
                "GroupChat.run", 
                wrap_groupchat_run(tracer, duration_histogram, token_histogram)
            )
            logger.info("Instrumented GroupChat.run")
        except Exception as e:
            logger.warning(f"Failed to instrument GroupChat.run: {e}")
        
        logger.info("AutoGen instrumentation complete")

    def _uninstrument(self, **kwargs):
        """Uninstrument AutoGen."""
        logger.info("Uninstrumenting AutoGen")
        
        # Uninstrument agent initialization
        unwrap_all_agent_methods()
        
        logger.info("AutoGen uninstrumentation complete")


def unwrap_all_agent_methods():
    """Unwrap all instrumented methods."""
    from wrapt import unwrap
    
    try:
        import autogen
        # Removed: unwrap(autogen.agentchat.conversable_agent.ConversableAgent, "__init__")
        unwrap(autogen.agentchat.conversable_agent.ConversableAgent, "generate_reply")
        unwrap(autogen.agentchat.conversable_agent.ConversableAgent, "generate_oai_reply")
        unwrap(autogen.agentchat.conversable_agent.ConversableAgent, "execute_function")
        unwrap(autogen.agentchat.groupchat.GroupChat, "run")
    except (AttributeError, NameError, ImportError) as e:
        logger.warning(f"Error during unwrapping: {e}")
        pass


def with_tracer_wrapper(func):
    """Decorator to create a wrapper function with tracer and metrics."""
    @functools.wraps(func)
    def _with_tracer(tracer, duration_histogram=None, token_histogram=None):
        @functools.wraps(func)
        def wrapper(wrapped, instance, args, kwargs):
            return func(tracer, duration_histogram, token_histogram, wrapped, instance, args, kwargs)
        return wrapper
    return _with_tracer


@with_tracer_wrapper
def wrap_agent_init(tracer: Tracer, duration_histogram: Optional[Histogram], token_histogram: Optional[Histogram],
                   wrapped, instance, args, kwargs):
    """Wrap agent initialization."""
    logger.debug(f"Creating span for agent initialization: {getattr(instance, 'name', 'unknown')}")
    with tracer.start_as_current_span(
        "autogen.agent.init",
        kind=SpanKind.INTERNAL,
        attributes={
            SpanAttributes.AGENTOPS_SPAN_KIND: AgentOpsSpanKindValues.AGENT.value,
        }
    ) as span:
        # Capture agent attributes
        result = wrapped(*args, **kwargs)
        
        # Set span attributes after initialization
        AutoGenSpanAttributes(span, instance)
        logger.debug(f"Agent initialization span completed for: {getattr(instance, 'name', 'unknown')}")
        
        return result


@with_tracer_wrapper
def wrap_generate_reply(tracer: Tracer, duration_histogram: Optional[Histogram], token_histogram: Optional[Histogram],
                       wrapped, instance, args, kwargs):
    """Wrap generate_reply method."""
    messages = args[0] if args else kwargs.get("messages", [])
    sender = args[1] if len(args) > 1 else kwargs.get("sender", "unknown")
    
    with tracer.start_as_current_span(
        "autogen.agent.generate_reply",
        kind=SpanKind.CLIENT,
        attributes={
            SpanAttributes.AGENTOPS_SPAN_KIND: AgentOpsSpanKindValues.AGENT.value,
            "agent.name": getattr(instance, "name", "unknown"),
            "agent.sender": getattr(sender, "name", str(sender)),
            "agent.message_count": len(messages) if isinstance(messages, list) else 1,
            "agent.description": getattr(instance, "description", ""),
        }
    ) as span:
        # Add LLM configuration information
        llm_config = getattr(instance, "llm_config", {})
        if llm_config:
            set_span_attribute(span, "llm.model", llm_config.get("model", "unknown"))
            set_span_attribute(span, "llm.temperature", llm_config.get("temperature", 0.7))
            set_span_attribute(span, "llm.provider", "openai")  # Default to OpenAI, could be different
            
            # Add any other LLM config parameters that might be useful
            for key in ["max_tokens", "top_p", "frequency_penalty", "presence_penalty"]:
                if key in llm_config:
                    set_span_attribute(span, f"llm.{key}", llm_config.get(key))
        
        # Capture system message if available
        system_message = getattr(instance, "system_message", None)
        if system_message:
            set_span_attribute(span, "agent.system_message", 
                              system_message[:1000] + "..." if len(system_message) > 1000 else system_message)
        
        # Capture input messages
        if messages and isinstance(messages, list):
            for i, msg in enumerate(messages[:5]):  # Limit to first 5 messages to avoid excessive data
                if hasattr(msg, "content") and msg.content:
                    content = str(msg.content)
                    set_span_attribute(span, f"input.message.{i}.content", 
                                     content[:500] + "..." if len(content) > 500 else content)
                if hasattr(msg, "source"):
                    set_span_attribute(span, f"input.message.{i}.source", getattr(msg, "source", "unknown"))
                if hasattr(msg, "type"):
                    set_span_attribute(span, f"input.message.{i}.type", getattr(msg, "type", "unknown"))
        
        # Capture agent state information if available
        if hasattr(instance, "save_state"):
            try:
                state = asyncio.run(instance.save_state())
                if state:
                    # Extract key state information without capturing everything
                    if "messages" in state and isinstance(state["messages"], list):
                        set_span_attribute(span, "agent.state.message_count", len(state["messages"]))
                    if "tools" in state and isinstance(state["tools"], list):
                        set_span_attribute(span, "agent.state.tool_count", len(state["tools"]))
            except Exception:
                pass
        
        start_time = time.time()
        result = wrapped(*args, **kwargs)
        duration = time.time() - start_time
        
        # Record duration metric
        if duration_histogram:
            duration_histogram.record(duration, {"operation": "generate_reply"})
        
        # Extract and record token usage using multiple approaches
        token_usage_found = False
        
        # Set message attributes
        if result:
            # Approach 1: Standard dictionary structure
            if isinstance(result, dict):
                # Extract and record message content
                if "content" in result and result["content"] is not None:
                    content = result["content"]
                    set_span_attribute(span, "message.content", 
                                      content[:1000] + "..." if len(content) > 1000 else content)
                
                # Extract and record token usage
                if "usage" in result:
                    usage = result["usage"]
                    token_usage_found = True
                    
                    if token_histogram and "total_tokens" in usage:
                        token_histogram.record(usage["total_tokens"], {"operation": "generate_reply"})
                    
                    set_span_attribute(span, "llm.token_usage.total", usage.get("total_tokens"))
                    set_span_attribute(span, "llm.token_usage.prompt", usage.get("prompt_tokens"))
                    set_span_attribute(span, "llm.token_usage.completion", usage.get("completion_tokens"))
                
                # Check for function calls in the response
                if "function_call" in result:
                    set_span_attribute(span, "message.has_function_call", True)
                    function_call = result["function_call"]
                    if isinstance(function_call, dict):
                        set_span_attribute(span, "message.function_call.name", function_call.get("name", "unknown"))
                        args_str = str(function_call.get("arguments", "{}"))
                        set_span_attribute(span, "message.function_call.arguments", 
                                         args_str[:500] + "..." if len(args_str) > 500 else args_str)
            
            # Approach 2: Object with attributes
            elif hasattr(result, "content"):
                content = result.content
                set_span_attribute(span, "message.content", 
                                  content[:1000] + "..." if len(content) > 1000 else content)
                
                # Try to get usage from result object
                if hasattr(result, "usage"):
                    usage = result.usage
                    token_usage_found = True
                    
                    # Try to extract token counts
                    if hasattr(usage, "total_tokens"):
                        set_span_attribute(span, "llm.token_usage.total", usage.total_tokens)
                        if token_histogram:
                            token_histogram.record(usage.total_tokens, {"operation": "generate_reply"})
                    if hasattr(usage, "prompt_tokens"):
                        set_span_attribute(span, "llm.token_usage.prompt", usage.prompt_tokens)
                    if hasattr(usage, "completion_tokens"):
                        set_span_attribute(span, "llm.token_usage.completion", usage.completion_tokens)
        
        # Approach 3: Try to get usage from the instance
        if not token_usage_found and hasattr(instance, "get_actual_usage"):
            try:
                usage = instance.get_actual_usage()
                if usage:
                    token_usage_found = True
                    set_span_attribute(span, "llm.token_usage.total", usage.get("total_tokens"))
                    set_span_attribute(span, "llm.token_usage.prompt", usage.get("prompt_tokens"))
                    set_span_attribute(span, "llm.token_usage.completion", usage.get("completion_tokens"))
            except Exception:
                pass
        
        # Approach 4: Try to get usage from the last message
        if not token_usage_found and hasattr(instance, "last_message"):
            try:
                last_message = instance.last_message()
                
                if hasattr(last_message, "usage"):
                    usage = last_message.usage
                    token_usage_found = True
                    
                    if hasattr(usage, "total_tokens"):
                        set_span_attribute(span, "llm.token_usage.total", usage.total_tokens)
                        if token_histogram:
                            token_histogram.record(usage.total_tokens, {"operation": "generate_reply"})
                    if hasattr(usage, "prompt_tokens"):
                        set_span_attribute(span, "llm.token_usage.prompt", usage.prompt_tokens)
                    if hasattr(usage, "completion_tokens"):
                        set_span_attribute(span, "llm.token_usage.completion", usage.completion_tokens)
                
                elif isinstance(last_message, dict) and "usage" in last_message:
                    usage = last_message["usage"]
                    token_usage_found = True
                    
                    set_span_attribute(span, "llm.token_usage.total", usage.get("total_tokens"))
                    set_span_attribute(span, "llm.token_usage.prompt", usage.get("prompt_tokens"))
                    set_span_attribute(span, "llm.token_usage.completion", usage.get("completion_tokens"))
            except Exception:
                pass
        
        # Set token usage found flag
        set_span_attribute(span, "llm.token_usage.found", token_usage_found)
        
        return result


@with_tracer_wrapper
def wrap_send(tracer: Tracer, duration_histogram: Optional[Histogram], token_histogram: Optional[Histogram],
             wrapped, instance, args, kwargs):
    """Wrap send method."""
    message = args[0] if args else kwargs.get("message", "")
    recipient = args[1] if len(args) > 1 else kwargs.get("recipient", "unknown")
    
    with tracer.start_as_current_span(
        "autogen.agent.send",
        kind=SpanKind.PRODUCER,
        attributes={
            SpanAttributes.AGENTOPS_SPAN_KIND: AgentOpsSpanKindValues.AGENT.value,
            "agent.name": getattr(instance, "name", "unknown"),
            "agent.recipient": getattr(recipient, "name", str(recipient)),
        }
    ) as span:
        # Set message attributes
        if isinstance(message, dict):
            for key, value in message.items():
                if key != "content":
                    set_span_attribute(span, f"message.{key}", value)
            
            if "content" in message and message["content"] is not None:
                content = message["content"]
                set_span_attribute(span, "message.content", 
                                  content[:1000] + "..." if len(content) > 1000 else content)
        elif isinstance(message, str):
            set_span_attribute(span, "message.content", 
                              message[:1000] + "..." if len(message) > 1000 else message)
        
        start_time = time.time()
        result = wrapped(*args, **kwargs)
        duration = time.time() - start_time
        
        # Record duration metric
        if duration_histogram:
            duration_histogram.record(duration, {"operation": "send"})
        
        return result


@with_tracer_wrapper
def wrap_receive(tracer: Tracer, duration_histogram: Optional[Histogram], token_histogram: Optional[Histogram],
               wrapped, instance, args, kwargs):
    """Wrap receive method."""
    message = args[0] if args else kwargs.get("message", "")
    sender = args[1] if len(args) > 1 else kwargs.get("sender", "unknown")
    
    with tracer.start_as_current_span(
        "autogen.agent.receive",
        kind=SpanKind.CONSUMER,
        attributes={
            SpanAttributes.AGENTOPS_SPAN_KIND: AgentOpsSpanKindValues.AGENT.value,
            "agent.name": getattr(instance, "name", "unknown"),
            "agent.sender": getattr(sender, "name", str(sender)),
        }
    ) as span:
        # Set message attributes
        if isinstance(message, dict):
            for key, value in message.items():
                if key != "content":
                    set_span_attribute(span, f"message.{key}", value)
            
            if "content" in message and message["content"] is not None:
                content = message["content"]
                set_span_attribute(span, "message.content", 
                                  content[:1000] + "..." if len(content) > 1000 else content)
        elif isinstance(message, str):
            set_span_attribute(span, "message.content", 
                              message[:1000] + "..." if len(message) > 1000 else message)
        
        result = wrapped(*args, **kwargs)
        return result


@with_tracer_wrapper
def wrap_generate_oai_reply(tracer: Tracer, duration_histogram: Optional[Histogram], token_histogram: Optional[Histogram],
                           wrapped, instance, args, kwargs):
    """Wrap generate_oai_reply method."""
    with tracer.start_as_current_span(
        "autogen.agent.generate_oai_reply",
        kind=SpanKind.CLIENT,
        attributes={
            SpanAttributes.AGENTOPS_SPAN_KIND: AgentOpsSpanKindValues.LLM.value,
            "agent.name": getattr(instance, "name", "unknown"),
            "agent.description": getattr(instance, "description", ""),
            "llm.provider": "openai",  # Assuming OpenAI, could be different
        }
    ) as span:
        # Extract model information if available
        llm_config = getattr(instance, "llm_config", {})
        if llm_config:
            set_span_attribute(span, "llm.model", llm_config.get("model", "unknown"))
            set_span_attribute(span, "llm.temperature", llm_config.get("temperature", 0.7))
            
            # Add any other LLM config parameters that might be useful
            for key in ["max_tokens", "top_p", "frequency_penalty", "presence_penalty"]:
                if key in llm_config:
                    set_span_attribute(span, f"llm.{key}", llm_config.get(key))
        
        # Capture system message if available
        system_message = getattr(instance, "system_message", None)
        if system_message:
            set_span_attribute(span, "agent.system_message", 
                              system_message[:1000] + "..." if len(system_message) > 1000 else system_message)
        
        # Extract messages from args or kwargs if available
        messages = None
        if args and len(args) > 0:
            messages = args[0]
        elif "messages" in kwargs:
            messages = kwargs["messages"]
        
        # Record input message count and approximate token count
        if messages and isinstance(messages, list):
            set_span_attribute(span, "llm.input.message_count", len(messages))
            
            # Capture detailed message information
            total_content_length = 0
            for i, msg in enumerate(messages[:10]):  # Limit to first 10 messages
                if isinstance(msg, dict):
                    # Capture message role
                    if "role" in msg:
                        set_span_attribute(span, f"llm.input.message.{i}.role", msg["role"])
                    
                    # Capture message content
                    if "content" in msg and msg["content"]:
                        content = str(msg["content"])
                        set_span_attribute(span, f"llm.input.message.{i}.content", 
                                         content[:500] + "..." if len(content) > 500 else content)
                        total_content_length += len(content)
                    
                    # Capture function calls in the message
                    if "function_call" in msg:
                        set_span_attribute(span, f"llm.input.message.{i}.has_function_call", True)
                        if isinstance(msg["function_call"], dict):
                            set_span_attribute(span, f"llm.input.message.{i}.function_call.name", 
                                             msg["function_call"].get("name", "unknown"))
            
            # Very rough approximation: 4 characters ~= 1 token
            estimated_tokens = total_content_length // 4
            set_span_attribute(span, "llm.input.estimated_tokens", estimated_tokens)
        
        # Capture model context information if available
        if hasattr(instance, "model_context") and getattr(instance, "model_context", None):
            model_context = getattr(instance, "model_context")
            if hasattr(model_context, "buffer_size"):
                set_span_attribute(span, "llm.model_context.buffer_size", getattr(model_context, "buffer_size"))
        
        # Capture tools information if available
        tools = getattr(instance, "tools", [])
        if tools:
            set_span_attribute(span, "agent.tools.count", len(tools))
            # Capture names of first few tools
            for i, tool in enumerate(tools[:5]):
                if hasattr(tool, "name"):
                    set_span_attribute(span, f"agent.tools.{i}.name", getattr(tool, "name"))
                elif hasattr(tool, "__name__"):
                    set_span_attribute(span, f"agent.tools.{i}.name", getattr(tool, "__name__"))
        
        start_time = time.time()
        result = wrapped(*args, **kwargs)
        duration = time.time() - start_time
        
        # Record duration metric
        if duration_histogram:
            duration_histogram.record(duration, {"operation": "generate_oai_reply"})
        
        # Extract and record token usage using multiple approaches
        token_usage_found = False
        
        # Approach 1: Try to get usage from the result object directly
        if result:
            # Try to access usage attribute
            if hasattr(result, "usage"):
                usage = result.usage
                token_usage_found = True
                
                if token_histogram and hasattr(usage, "total_tokens"):
                    token_histogram.record(usage.total_tokens, {"operation": "generate_oai_reply"})
                
                set_span_attribute(span, "llm.token_usage.total", getattr(usage, "total_tokens", None))
                set_span_attribute(span, "llm.token_usage.prompt", getattr(usage, "prompt_tokens", None))
                set_span_attribute(span, "llm.token_usage.completion", getattr(usage, "completion_tokens", None))
                
                # Calculate cost if possible (very rough estimate)
                if hasattr(usage, "total_tokens") and hasattr(usage, "prompt_tokens") and hasattr(usage, "completion_tokens"):
                    model = llm_config.get("model", "").lower() if llm_config else ""
                    if "gpt-4" in model:
                        # GPT-4 pricing (very approximate)
                        prompt_cost = usage.prompt_tokens * 0.00003
                        completion_cost = usage.completion_tokens * 0.00006
                        total_cost = prompt_cost + completion_cost
                        set_span_attribute(span, "llm.estimated_cost_usd", round(total_cost, 6))
                    elif "gpt-3.5" in model:
                        # GPT-3.5 pricing (very approximate)
                        prompt_cost = usage.prompt_tokens * 0.000001
                        completion_cost = usage.completion_tokens * 0.000002
                        total_cost = prompt_cost + completion_cost
                        set_span_attribute(span, "llm.estimated_cost_usd", round(total_cost, 6))
        
        # Approach 2: Try to get usage from the instance
        if not token_usage_found and hasattr(instance, "get_actual_usage"):
            try:
                usage = instance.get_actual_usage()
                if usage:
                    token_usage_found = True
                    set_span_attribute(span, "llm.token_usage.total", usage.get("total_tokens"))
                    set_span_attribute(span, "llm.token_usage.prompt", usage.get("prompt_tokens"))
                    set_span_attribute(span, "llm.token_usage.completion", usage.get("completion_tokens"))
            except Exception:
                pass
        
        # Approach 3: Try to access token usage from response dictionary
        if not token_usage_found and hasattr(result, "__dict__"):
            try:
                result_dict = result.__dict__
                if "usage" in result_dict and isinstance(result_dict["usage"], dict):
                    usage = result_dict["usage"]
                    token_usage_found = True
                    set_span_attribute(span, "llm.token_usage.total", usage.get("total_tokens"))
                    set_span_attribute(span, "llm.token_usage.prompt", usage.get("prompt_tokens"))
                    set_span_attribute(span, "llm.token_usage.completion", usage.get("completion_tokens"))
            except Exception:
                pass
        
        # Approach 4: Try to convert result to dictionary if it's JSON serializable
        if not token_usage_found:
            try:
                if hasattr(result, "model_dump"):  # Pydantic v2
                    result_dict = result.model_dump()
                elif hasattr(result, "dict"):  # Pydantic v1
                    result_dict = result.dict()
                else:
                    # Try to convert to dict using json
                    result_dict = json.loads(json.dumps(result, default=lambda o: o.__dict__ if hasattr(o, "__dict__") else str(o)))
                
                if isinstance(result_dict, dict) and "usage" in result_dict and isinstance(result_dict["usage"], dict):
                    usage = result_dict["usage"]
                    token_usage_found = True
                    set_span_attribute(span, "llm.token_usage.total", usage.get("total_tokens"))
                    set_span_attribute(span, "llm.token_usage.prompt", usage.get("prompt_tokens"))
                    set_span_attribute(span, "llm.token_usage.completion", usage.get("completion_tokens"))
            except Exception:
                pass
        
        # Set token usage found flag
        set_span_attribute(span, "llm.token_usage.found", token_usage_found)
        
        # Extract and record response content
        if result:
            # Try to get choices from the result
            choices = None
            if hasattr(result, "choices"):
                choices = result.choices
            elif hasattr(result, "__dict__") and "choices" in result.__dict__:
                choices = result.__dict__["choices"]
            
            if choices and len(choices) > 0:
                choice = choices[0]
                
                # Try different approaches to extract message content
                content = None
                
                # Approach 1: Standard OpenAI structure
                if hasattr(choice, "message") and hasattr(choice.message, "content"):
                    content = choice.message.content
                
                # Approach 2: Dict-like structure
                elif hasattr(choice, "__dict__") and "message" in choice.__dict__:
                    message = choice.__dict__["message"]
                    if hasattr(message, "content"):
                        content = message.content
                    elif hasattr(message, "__dict__") and "content" in message.__dict__:
                        content = message.__dict__["content"]
                
                # Approach 3: Direct content attribute
                elif hasattr(choice, "content"):
                    content = choice.content
                
                # Record content if found
                if content:
                    set_span_attribute(span, "llm.response.content", 
                                      content[:1000] + "..." if len(content) > 1000 else content)
                    
                    # Estimate output token count
                    estimated_output_tokens = len(str(content)) // 4
                    set_span_attribute(span, "llm.output.estimated_tokens", estimated_output_tokens)
                
                # Extract finish reason using multiple approaches
                finish_reason = None
                if hasattr(choice, "finish_reason"):
                    finish_reason = choice.finish_reason
                elif hasattr(choice, "__dict__") and "finish_reason" in choice.__dict__:
                    finish_reason = choice.__dict__["finish_reason"]
                
                if finish_reason:
                    set_span_attribute(span, "llm.response.finish_reason", finish_reason)
                
                # Check for function calls using multiple approaches
                function_call = None
                if hasattr(choice, "message") and hasattr(choice.message, "function_call"):
                    function_call = choice.message.function_call
                elif hasattr(choice, "__dict__") and "message" in choice.__dict__:
                    message = choice.__dict__["message"]
                    if hasattr(message, "function_call"):
                        function_call = message.function_call
                    elif hasattr(message, "__dict__") and "function_call" in message.__dict__:
                        function_call = message.__dict__["function_call"]
                
                if function_call:
                    set_span_attribute(span, "llm.response.has_function_call", True)
                    
                    # Extract function name
                    function_name = None
                    if hasattr(function_call, "name"):
                        function_name = function_call.name
                    elif hasattr(function_call, "__dict__") and "name" in function_call.__dict__:
                        function_name = function_call.__dict__["name"]
                    
                    if function_name:
                        set_span_attribute(span, "llm.response.function_name", function_name)
                    
                    # Extract function arguments
                    function_args = None
                    if hasattr(function_call, "arguments"):
                        function_args = function_call.arguments
                    elif hasattr(function_call, "__dict__") and "arguments" in function_call.__dict__:
                        function_args = function_call.__dict__["arguments"]
                    
                    if function_args:
                        args_str = str(function_args)
                        set_span_attribute(span, "llm.response.function_arguments", 
                                         args_str[:500] + "..." if len(args_str) > 500 else args_str)
        
        return result


@with_tracer_wrapper
def wrap_call_function(tracer: Tracer, duration_histogram: Optional[Histogram], token_histogram: Optional[Histogram],
                      wrapped, instance, args, kwargs):
    """Wrap execute_function method."""
    function_name = args[0] if args else kwargs.get("function_name", "unknown")
    
    with tracer.start_as_current_span(
        "autogen.agent.execute_function",
        kind=SpanKind.INTERNAL,
        attributes={
            SpanAttributes.AGENTOPS_SPAN_KIND: AgentOpsSpanKindValues.TOOL.value,
            "agent.name": getattr(instance, "name", "unknown"),
            "tool.name": function_name,
        }
    ) as span:
        # Extract function arguments
        arguments = args[1] if len(args) > 1 else kwargs.get("arguments", {})
        set_span_attribute(span, "tool.arguments", arguments)
        
        start_time = time.time()
        result = wrapped(*args, **kwargs)
        duration = time.time() - start_time
        
        # Record duration metric
        if duration_histogram:
            duration_histogram.record(duration, {"operation": "execute_function"})
        
        # Record function result
        if result is not None:
            if isinstance(result, str):
                set_span_attribute(span, "tool.result", 
                                  result[:1000] + "..." if len(result) > 1000 else result)
            else:
                set_span_attribute(span, "tool.result", str(result))
        
        return result


@with_tracer_wrapper
def wrap_initiate_chat(tracer: Tracer, duration_histogram: Optional[Histogram], token_histogram: Optional[Histogram],
                      wrapped, instance, args, kwargs):
    """Wrap initiate_chat method."""
    recipient = args[0] if args else kwargs.get("recipient", "unknown")
    message = args[1] if len(args) > 1 else kwargs.get("message", "")
    
    with tracer.start_as_current_span(
        "autogen.agent.initiate_chat",
        kind=SpanKind.INTERNAL,
        attributes={
            SpanAttributes.AGENTOPS_SPAN_KIND: AgentOpsSpanKindValues.AGENT.value,
            "agent.name": getattr(instance, "name", "unknown"),
            "agent.recipient": getattr(recipient, "name", str(recipient)),
        }
    ) as span:
        # Set message attributes
        if isinstance(message, str):
            set_span_attribute(span, "message.content", 
                              message[:1000] + "..." if len(message) > 1000 else message)
        
        start_time = time.time()
        result = wrapped(*args, **kwargs)
        duration = time.time() - start_time
        
        # Record duration metric
        if duration_histogram:
            duration_histogram.record(duration, {"operation": "initiate_chat"})
        
        return result


@with_tracer_wrapper
def wrap_groupchat_run(tracer: Tracer, duration_histogram: Optional[Histogram], token_histogram: Optional[Histogram],
                      wrapped, instance, args, kwargs):
    """Wrap GroupChat.run method."""
    with tracer.start_as_current_span(
        "autogen.team.groupchat.run",
        kind=SpanKind.INTERNAL,
        attributes={
            SpanAttributes.AGENTOPS_SPAN_KIND: AgentOpsSpanKindValues.TEAM.value,
            "team.name": getattr(instance, "name", "unknown"),
            "team.agents_count": len(getattr(instance, "agents", [])),
        }
    ) as span:
        # Set group chat attributes
        try:
            AutoGenSpanAttributes(span, instance)
        except Exception:
            pass
        
        start_time = time.time()
        result = wrapped(*args, **kwargs)
        duration = time.time() - start_time
        
        # Record duration metric
        if duration_histogram:
            duration_histogram.record(duration, {"operation": "groupchat_run"})
        
        return result


@with_tracer_wrapper
def wrap_groupchat_manager_run(tracer: Tracer, duration_histogram: Optional[Histogram], token_histogram: Optional[Histogram],
                              wrapped, instance, args, kwargs):
    """Wrap GroupChatManager.run method."""
    with tracer.start_as_current_span(
        "autogen.team.groupchat_manager.run",
        kind=SpanKind.INTERNAL,
        attributes={
            SpanAttributes.AGENTOPS_SPAN_KIND: AgentOpsSpanKindValues.TEAM.value,
            "team.manager.name": getattr(instance, "name", "unknown"),
        }
    ) as span:
        # Set group chat manager attributes
        AutoGenSpanAttributes(span, instance)
        
        start_time = time.time()
        result = wrapped(*args, **kwargs)
        duration = time.time() - start_time
        
        # Record duration metric
        if duration_histogram:
            duration_histogram.record(duration, {"operation": "groupchat_manager_run"})
        
        return result


def is_metrics_enabled() -> bool:
    """Check if metrics are enabled."""
    try:
        from opentelemetry.metrics import get_meter_provider
        from opentelemetry.sdk.metrics import MeterProvider
        return not isinstance(get_meter_provider(), MeterProvider)
    except ImportError:
        return False


def _create_metrics(meter: Meter):
    """Create metrics for AutoGen."""
    token_histogram = meter.create_histogram(
        name=Meters.LLM_TOKEN_USAGE,
        unit="token",
        description="Measures number of input and output tokens used",
    )

    duration_histogram = meter.create_histogram(
        name=Meters.LLM_OPERATION_DURATION,
        unit="s",
        description="AutoGen operation duration",
    )

    return token_histogram, duration_histogram 