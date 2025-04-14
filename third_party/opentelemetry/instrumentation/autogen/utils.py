"""
Module for monitoring AG2 API calls.
"""
import json
import logging
import time
from opentelemetry.trace import SpanKind, Status, StatusCode, get_tracer_provider
from opentelemetry.sdk.resources import SERVICE_NAME, TELEMETRY_SDK_NAME, DEPLOYMENT_ENVIRONMENT
from agentops.semconv import SpanAttributes
from agentops.semconv.message import MessageAttributes
from typing import Dict, Any, Optional, Tuple
from agentops.instrumentation.common.attributes import AttributeMap
from typing import List
# Initialize logger for logging potential issues and operations
logger = logging.getLogger(__name__)

AGENT_NAME = ""
REQUEST_MODEL = ""
SYSTEM_MESSAGE = ""
MODEL_AND_NAME_SET = False


def set_span_attributes(span, version, operation_name, environment, application_name, request_model):
    """
    Set common attributes for the span.
    """

    # Set Span attributes (OTel Semconv)
    span.set_attribute(TELEMETRY_SDK_NAME, "agentops")
    span.set_attribute(SpanAttributes.GEN_AI_OPERATION, operation_name)
    span.set_attribute(SpanAttributes.GEN_AI_SYSTEM, SpanAttributes.GEN_AI_SYSTEM_AG2)
    span.set_attribute(SpanAttributes.GEN_AI_AGENT_NAME, AGENT_NAME)
    span.set_attribute(SpanAttributes.GEN_AI_REQUEST_MODEL, request_model)

    # Set Span attributes (Extras)
    span.set_attribute(DEPLOYMENT_ENVIRONMENT, environment)
    span.set_attribute(SERVICE_NAME, application_name)
    span.set_attribute(SpanAttributes.GEN_AI_SDK_VERSION, version)


def conversable_agent(
    version,
    environment,
    application_name,
    tracer,
    event_provider,
    pricing_info,
    capture_message_content,
    metrics,
    disable_metrics,
):
    """
    Generates a telemetry wrapper for GenAI function call
    """

    def wrapper(wrapped, instance, args, kwargs):
        global AGENT_NAME, MODEL_AND_NAME_SET, REQUEST_MODEL, SYSTEM_MESSAGE

        if not MODEL_AND_NAME_SET:
            AGENT_NAME = kwargs.get("name", "NOT_FOUND")
            REQUEST_MODEL = kwargs.get("llm_config", {}).get("model", "gpt-4o")
            SYSTEM_MESSAGE = kwargs.get("system_message", "")
            MODEL_AND_NAME_SET = True

        with tracer.start_as_current_span(
            "autogen.workflow", kind=SpanKind.CLIENT, attributes={SpanAttributes.LLM_SYSTEM: "autogen"}
        ) as span:
            request_attributes = get_message_request_attributes(kwargs)
            for key, value in request_attributes.items():
                span.set_attribute(key, value)

            try:
                start_time = time.time()
                response = wrapped(*args, **kwargs)  # This should be the actual function call
                end_time = time.time()

                # Check if the response is None here and log it
                if response is None:
                    print("The wrapped function returned None.")

                
                set_span_attributes(
                    span,
                    version,
                    SpanAttributes.GEN_AI_OPERATION_TYPE_CREATE_AGENT,
                    environment,
                    application_name,
                    REQUEST_MODEL,
                )
                span.set_attribute(SpanAttributes.GEN_AI_AGENT_DESCRIPTION, SYSTEM_MESSAGE)
                span.set_attribute(SpanAttributes.GEN_AI_RESPONSE_MODEL, REQUEST_MODEL)
                span.set_attribute(SpanAttributes.GEN_AI_SERVER_TTFT, end_time - start_time)

                span.set_attribute("span_name", "autogen.workflow")

                if response:
                    class_name = instance.__class__.__name__
                    span.set_attribute(f"autogen.{class_name.lower()}.result", str(response))
                    span.set_status(Status(StatusCode.OK))
                    if class_name == "ConversableAgent":
                        # Handle 'chat_history'
                        if hasattr(response, "chat_history"):
                            chat_history = response.chat_history
                            # You can stringify the list or extract specific details, like content
                            chat_history_str = " | ".join(
                                [f"{entry['role']}: {entry['content']}" for entry in chat_history]
                            )
                            span.set_attribute("autogen.conversable_agent.chat_history", chat_history_str)

                        # Handle 'token_usage' from the top level 'total_cost'
                        if hasattr(response, "cost"):
                            # Get total_cost directly from the top level
                            model_keys = [key for key in response.cost.keys() if key == 'usage_including_cached_inference']
                            total_cost = response.cost[model_keys[0]].get("total_cost", 0)
                            span.set_attribute("autogen.conversable_agent.token_usage", f"Total cost: {total_cost}")

                        # Handle 'usage_metrics' from dynamic model key inside the 'cost' field
                        if hasattr(response, "cost"):
                            # Find the model key (the key that isn't 'total_cost')
                            model_keys = [key for key in response.cost.keys() if key != 'total_cost']
                            if model_keys:
                                model_key = model_keys[0]  # Get the first (and likely only) model key
                                
                                whole_usage_metrics = response.cost[model_key]
                                model_data = [key for key in whole_usage_metrics.keys() if key != 'total_cost']
                                
                                usage_metricss = whole_usage_metrics.get(model_data[0], {})
                                
                                prompt_tokens = usage_metricss.get("prompt_tokens", 0)
                                completion_tokens = usage_metricss.get("completion_tokens", 0)
                                total_tokens = usage_metricss.get("total_tokens", 0)
                                span.set_attribute(
                                    "autogen.conversable_agent.usage_metrics",
                                    f"Prompt Tokens: {prompt_tokens}, Completion Tokens: {completion_tokens}, Total Tokens: {total_tokens}",
                                )   
                                
                                span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, prompt_tokens)
                                span.set_attribute(SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, completion_tokens)
                                span.set_attribute(SpanAttributes.LLM_USAGE_TOTAL_TOKENS, total_tokens)

                span.set_status(Status(StatusCode.OK))
                
                
                return response

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                logger.error("Error in trace creation: %s", e)

    return wrapper

def get_message_request_attributes(kwargs: Dict[str, Any]) -> AttributeMap:
    """Extract attributes from message request parameters.
    
    This function processes the request parameters for the Messages API call and extracts
    standardized attributes for telemetry. It handles different message formats including
    system prompts, user/assistant messages, and tool-using messages.
    
    It extracts:
    - System prompt (if present)
    - User and assistant messages
    - Tool definitions (if present)
    - Model parameters (temperature, max_tokens, etc.)
    
    Args:
        kwargs: Request keyword arguments
        
    Returns:
        Dictionary of extracted attributes
    """
    attributes = extract_request_attributes(kwargs=kwargs)
    
    # Extract system prompt if present
    system = kwargs.get("system", "")
    if system:
        attributes[MessageAttributes.PROMPT_ROLE.format(i=0)] = "system"
        attributes[MessageAttributes.PROMPT_CONTENT.format(i=0)] = system
        attributes[MessageAttributes.PROMPT_TYPE.format(i=0)] = "text"
    
    # Extract messages
    messages = kwargs.get("messages", [])
    for index, msg in enumerate(messages):
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        # Process content and extract attributes
        content_attributes = _process_content(content, role, index)
        attributes.update(content_attributes)
    
    # Extract tools if present
    tools = kwargs.get("tools", [])
    if tools:
        tool_attributes = extract_tool_definitions(tools)
        attributes.update(tool_attributes)
    
    return attributes




def _process_content(content, role, index):
    """Helper function to process content and extract attributes.
    
    Args:
        content: The content to process
        role: The role of the message
        index: The index of the message
        
    Returns:
        Dictionary of attributes for this content
    """
    attributes = {}
    
    if isinstance(content, str):
        # String content is easy
        attributes[MessageAttributes.PROMPT_ROLE.format(i=index)] = role
        attributes[MessageAttributes.PROMPT_CONTENT.format(i=index)] = content
        attributes[MessageAttributes.PROMPT_TYPE.format(i=index)] = "text"
    elif isinstance(content, list):
        # For list content, create a simplified representation
        content_str = ""
        for item in content:
            if isinstance(item, dict) and "type" in item:
                if item["type"] == "text" and "text" in item:
                    content_str += item["text"] + " "
                elif item["type"] == "tool_result" and "content" in item:
                    content_str += f"[Tool Result: {str(item['content'])}] "
            elif hasattr(item, "type"):
                if item.type == "text" and hasattr(item, "text"):
                    content_str += item.text + " "
        
        attributes[MessageAttributes.PROMPT_ROLE.format(i=index)] = role
        attributes[MessageAttributes.PROMPT_CONTENT.format(i=index)] = content_str.strip()
        attributes[MessageAttributes.PROMPT_TYPE.format(i=index)] = "text"
    else:
        # Other types - try to convert to string
        try:
            simple_content = str(content)
            attributes[MessageAttributes.PROMPT_ROLE.format(i=index)] = role
            attributes[MessageAttributes.PROMPT_CONTENT.format(i=index)] = simple_content
            attributes[MessageAttributes.PROMPT_TYPE.format(i=index)] = "text"
        except:
            # Ultimate fallback
            attributes[MessageAttributes.PROMPT_ROLE.format(i=index)] = role
            attributes[MessageAttributes.PROMPT_CONTENT.format(i=index)] = "(complex content)"
            attributes[MessageAttributes.PROMPT_TYPE.format(i=index)] = "unknown"
    
    return attributes




def extract_tool_definitions(tools: List[Dict[str, Any]]) -> AttributeMap:
    """Extract attributes from tool definitions.
    
    Processes a list of Autogen tool definitions and converts them into
    standardized attributes for OpenTelemetry instrumentation. This captures
    information about each tool's name, description, and input schema.
    
    Args:
        tools: List of tool definition objects
        
    Returns:
        Dictionary of tool-related attributes
    """
    attributes = {}
    
    try:
        if not tools:
            return attributes
        
        for i, tool in enumerate(tools):
            name = tool.get("name", "unknown")
            description = tool.get("description", "")
            
            attributes[MessageAttributes.TOOL_CALL_NAME.format(i=i)] = name
            attributes[MessageAttributes.TOOL_CALL_TYPE.format(i=i)] = "function"
            
            if description:
                attributes[MessageAttributes.TOOL_CALL_DESCRIPTION.format(i=i)] = description
            
            if "input_schema" in tool:
                attributes[MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=i)] = json.dumps(tool["input_schema"])
            
            tool_id = tool.get("id", f"tool-{i}")
            attributes[MessageAttributes.TOOL_CALL_ID.format(i=i)] = tool_id
            attributes[MessageAttributes.TOOL_CALL_NAME.format(i=i)] = name
            if description:
                attributes[MessageAttributes.TOOL_CALL_DESCRIPTION.format(i=i)] = description
        
        tool_names = [tool.get("name", "unknown") for tool in tools]
        attributes[SpanAttributes.LLM_REQUEST_FUNCTIONS] = json.dumps(tool_names)
        
        tool_schemas = []
        for tool in tools:
            schema = {
                "name": tool.get("name", "unknown"),
                "schema": {}
            }
            
            if "description" in tool:
                schema["schema"]["description"] = tool["description"]
            if "input_schema" in tool:
                schema["schema"]["input_schema"] = tool["input_schema"]
            
            tool_schemas.append(schema)
            
        attributes["autogen.tools.schemas"] = json.dumps(tool_schemas)
        
    except Exception as e:
        logger.debug(f"[agentops.instrumentation.autogen] Error extracting tool definitions: {e}")
    
    return attributes


def extract_request_attributes(kwargs: Dict[str, Any]) -> AttributeMap:
    """Extract all request attributes from kwargs.
    
    This consolidated function extracts all relevant attributes from the request
    kwargs, including model, system prompt, messages, max_tokens, temperature,
    and other parameters. It replaces the individual extraction functions with
    a single comprehensive approach.
    
    Args:
        kwargs: Request keyword arguments
        
    Returns:
        Dictionary of extracted request attributes
    """
    attributes = {}
    
    # Extract model
    if 'model' in kwargs:
        attributes[SpanAttributes.LLM_REQUEST_MODEL] = kwargs["model"]
    
    # Extract max_tokens
    if 'max_tokens' in kwargs:
        attributes[SpanAttributes.LLM_REQUEST_MAX_TOKENS] = kwargs["max_tokens"]
    
    # Extract temperature
    if 'temperature' in kwargs:
        attributes[SpanAttributes.LLM_REQUEST_TEMPERATURE] = kwargs["temperature"]
    
    # Extract top_p
    if "top_p" in kwargs:
        attributes[SpanAttributes.LLM_REQUEST_TOP_P] = kwargs["top_p"]
    
    # Extract streaming
    if "stream" in kwargs:
        attributes[SpanAttributes.LLM_REQUEST_STREAMING] = kwargs["stream"]
    
    return attributes