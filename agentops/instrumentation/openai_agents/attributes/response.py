from typing import Any, List
from agentops.logging import logger
from agentops.helpers import safe_serialize
from agentops.semconv import (
    SpanAttributes, 
    MessageAttributes, 
    ToolAttributes, 
)
from agentops.instrumentation.openai_agents.attributes import (
    AttributeMap, 
    _extract_attributes_from_mapping, 
)

try:
    from openai.types import Reasoning
    from openai.types.beta import FunctionTool  # TODO beta will likely change
    from openai.types.responses import (
        Response, 
        ResponseUsage, 
        ResponseOutputMessage, 
        ResponseOutputText, 
        ResponseReasoningItem, 
        ResponseFunctionToolCall, 
        # ResponseComputerToolCall,
        # ResponseFileSearchToolCall,
        # ResponseFunctionWebSearch,
        # ResponseInputItemParam,
        # ResponseOutputItem,
        # ResponseOutputRefusal,
        # ResponseStreamEvent,
    )
    from openai.types.responses.response_usage import OutputTokensDetails
except ImportError as e:
    logger.debug(f"[agentops.instrumentation.openai_agents] Could not import OpenAI Agents SDK types: {e}")


RESPONSE_ATTRIBUTES: AttributeMap = {
    SpanAttributes.LLM_RESPONSE_ID: "id",
    SpanAttributes.LLM_REQUEST_MODEL: "model",
    SpanAttributes.LLM_RESPONSE_MODEL: "model",
    SpanAttributes.LLM_PROMPTS: "instructions",
    SpanAttributes.LLM_REQUEST_MAX_TOKENS: "max_output_tokens",
    SpanAttributes.LLM_REQUEST_TEMPERATURE: "temperature",
    SpanAttributes.LLM_REQUEST_TOP_P: "top_p",
}


RESPONSE_TOOLS_ATTRIBUTES: AttributeMap = {
    ToolAttributes.TOOL_NAME: "name",
    ToolAttributes.TOOL_DESCRIPTION: "description",
    ToolAttributes.TOOL_PARAMETERS: "parameters",
    # TODO `type` & `strict` are not converted
}


RESPONSE_OUTPUT_ATTRIBUTES: AttributeMap = {
    MessageAttributes.COMPLETION_ID: "id",
}


RESPONSE_OUTPUT_MESSAGE_ATTRIBUTES: AttributeMap = {
    MessageAttributes.COMPLETION_ID: "id",
    MessageAttributes.COMPLETION_ROLE: "role",
    MessageAttributes.COMPLETION_FINISH_REASON: "status",
    MessageAttributes.COMPLETION_TYPE: "type",
}


RESPONSE_OUTPUT_TEXT_ATTRIBUTES: AttributeMap = {
    MessageAttributes.COMPLETION_CONTENT: "text",
}


RESPONSE_OUTPUT_TOOL_ATTRIBUTES: AttributeMap = {
    MessageAttributes.FUNCTION_CALL_ID: "id",
    MessageAttributes.FUNCTION_CALL_NAME: "name",
    MessageAttributes.FUNCTION_CALL_ARGUMENTS: "arguments",
    MessageAttributes.FUNCTION_CALL_TYPE: "type",
    # TODO `status` & `call_id` are not converted
}


RESPONSE_OUTPUT_REASONING_ATTRIBUTES: AttributeMap = {
    # TODO we don't have semantic conventions for these
    # TODO `id`, `summary`, `type`, `status` are not converted
}


RESPONSE_USAGE_ATTRIBUTES: AttributeMap = {
    SpanAttributes.LLM_USAGE_COMPLETION_TOKENS: "output_tokens",
    SpanAttributes.LLM_USAGE_PROMPT_TOKENS: "input_tokens",
    SpanAttributes.LLM_USAGE_TOTAL_TOKENS: "total_tokens",
}


# usage attributes are shared with `input_details_tokens` and `output_details_tokens`
RESPONSE_USAGE_DETAILS_ATTRIBUTES: AttributeMap = {
    SpanAttributes.LLM_USAGE_CACHE_READ_INPUT_TOKENS: "cached_tokens",
    SpanAttributes.LLM_USAGE_REASONING_TOKENS: "reasoning_tokens",
}


RESPONSE_REASONING_ATTRIBUTES: AttributeMap = {
    # TODO `effort` and `generate_summary` are not converted
}


def get_response_response_attributes(response: 'Response') -> AttributeMap:
    """Handles interpretation of an openai Response object."""
    # Response(
    #     id='resp_67ddd0196a4c81929f7e3783a80f18110b486458d6766f93', 
    #     created_at=1742589977.0, 
    #     error=None, 
    #     incomplete_details=None, 
    #     instructions='You are a helpful assistant...', 
    #     metadata={}, 
    #     model='gpt-4o-2024-08-06', 
    #     object='response', 
    #     output=[
    #         ...
    #     ], 
    #     parallel_tool_calls=True, 
    #     temperature=1.0, 
    #     tool_choice='auto', 
    #     tools=[
    #         ...)
    #     ], 
    #     top_p=1.0, 
    #     max_output_tokens=None, 
    #     previous_response_id=None, 
    #     reasoning=Reasoning(
    #         ...
    #     ), 
    #     status='completed', 
    #     text=ResponseTextConfig(format=ResponseFormatText(type='text')), 
    #     truncation='disabled', 
    #     usage=ResponseUsage(
    #         ...
    #     ), 
    #     user=None, 
    #     store=True
    # )
    attributes = _extract_attributes_from_mapping(
        response.__dict__, 
        RESPONSE_ATTRIBUTES)
    
    if response.output:
        attributes.update(get_response_output_attributes(response.output))
    
    if response.tools:
        attributes.update(get_response_tools_attributes(response.tools))
    
    if response.reasoning:
        attributes.update(get_response_reasoning_attributes(response.reasoning))
    
    if response.usage:
        attributes.update(get_response_usage_attributes(response.usage))
    
    return attributes


def get_response_output_attributes(output: List[Any]) -> AttributeMap:
    """Handles interpretation of an openai Response `output` list."""
    attributes = {}
    
    for i, output_item in enumerate(output):
        if isinstance(output_item, ResponseOutputMessage):
            attributes.update(get_response_output_message_attributes(i, output_item))
        elif isinstance(output_item, ResponseReasoningItem):
            attributes.update(get_response_output_reasoning_attributes(i, output_item))
        elif isinstance(output_item, ResponseFunctionToolCall):
            attributes.update(get_response_output_tool_attributes(i, output_item))
        else:
            logger.debug(f"[agentops.instrumentation.openai_agents] '{output_item}' is not a recognized output type.")

    return attributes


def get_response_output_message_attributes(index: int, message: 'ResponseOutputMessage') -> AttributeMap:
    """Handles interpretation of an openai ResponseOutputMessage object."""
    # ResponseOutputMessage(
    #     id='msg_67ddcad3b6008192b521035d8b71fc570db7bfce93fd916a', 
    #     content=[
    #         ...
    #     ], 
    #     role='assistant', 
    #     status='completed', 
    #     type='message'
    # )
    attributes = {}
    
    for attribute, lookup in RESPONSE_OUTPUT_MESSAGE_ATTRIBUTES.items():
        if hasattr(message, lookup):
            attributes[attribute.format(i=index)] = safe_serialize(getattr(message, lookup))
    
    if message.content:
        for i, content in enumerate(message.content):
            if isinstance(content, ResponseOutputText):
                attributes.update(get_response_output_text_attributes(i, content))
            else:
                logger.debug(f"[agentops.instrumentation.openai_agents] '{content}' is not a recognized content type.")
    
    return attributes


def get_response_output_text_attributes(index: int, content: 'ResponseOutputText') -> AttributeMap:
    """Handles interpretation of an openai ResponseOutputText object."""
    # ResponseOutputText(
    #     annotations=[], 
    #     text='Recursion is a programming technique ...', 
    #     type='output_text'
    # )
    attributes = {}
    
    for attribute, lookup in RESPONSE_OUTPUT_TEXT_ATTRIBUTES.items():
        if hasattr(content, lookup):
            attributes[attribute.format(i=index)] = safe_serialize(getattr(content, lookup))
    
    return attributes


def get_response_output_reasoning_attributes(index: int, output: 'ResponseReasoningItem') -> AttributeMap:
    """Handles interpretation of an openai ResponseReasoningItem object."""
    # Reasoning(
    #     effort=None, 
    #     generate_summary=None
    # )
    attributes = {}
    
    for attribute, lookup in RESPONSE_OUTPUT_REASONING_ATTRIBUTES.items():
        if hasattr(output, lookup):
            attributes[attribute.format(i=index)] = safe_serialize(getattr(output, lookup))
    
    return attributes


def get_response_output_tool_attributes(index: int, output: 'ResponseFunctionToolCall') -> AttributeMap:
    """Handles interpretation of an openai ResponseFunctionToolCall object."""
    # FunctionTool(
    #     name='get_weather', 
    #     parameters={'properties': {'location': {'title': 'Location', 'type': 'string'}}, 'required': ['location'], 'title': 'get_weather_args', 'type': 'object', 'additionalProperties': False}, 
    #     strict=True, 
    #     type='function', 
    #     description='Get the current weather for a location.'
    # )
    attributes = {}
    
    for attribute, lookup in RESPONSE_OUTPUT_TOOL_ATTRIBUTES.items():
        if hasattr(output, lookup):
            attributes[attribute.format(i=index)] = safe_serialize(getattr(output, lookup))
    
    return attributes


def get_response_tools_attributes(tools: List[Any]) -> AttributeMap:
    """Handles interpretation of openai Response `tools` list."""
    # FunctionTool(
    #     name='get_weather', 
    #     parameters={'properties': {'location': {'title': 'Location', 'type': 'string'}}, 'required': ['location'], 'title': 'get_weather_args', 'type': 'object', 'additionalProperties': False}, 
    #     strict=True, 
    #     type='function', 
    #     description='Get the current weather for a location.'
    # )
    attributes = {}
    
    for i, tool in enumerate(tools):
        if isinstance(tool, FunctionTool):
            # FunctionTool(
            #     name='get_weather', 
            #     parameters={'properties': {'location': {'title': 'Location', 'type': 'string'}}, 'required': ['location'], 'title': 'get_weather_args', 'type': 'object', 'additionalProperties': False}, 
            #     strict=True, 
            #     type='function', 
            #     description='Get the current weather for a location.'
            # )
            for attribute, lookup in RESPONSE_TOOLS_ATTRIBUTES.items():
                if not hasattr(tool, lookup):
                    continue
                
                attributes[attribute.format(i=i)] = safe_serialize(getattr(tool, lookup))
        else:
            logger.debug(f"[agentops.instrumentation.openai_agents] '{tool}' is not a recognized tool type.")
    
    return attributes


def get_response_usage_attributes(usage: 'ResponseUsage') -> AttributeMap:
    """Handles interpretation of an openai ResponseUsage object."""
    # ResponseUsage(
    #     input_tokens=0, 
    #     output_tokens=0, 
    #     output_tokens_details=OutputTokensDetails(reasoning_tokens=0), 
    #     total_tokens=0, 
    #     input_tokens_details={'cached_tokens': 0}
    # )
    attributes = {}
    
    # input_tokens_details is a dict if it exists
    if hasattr(usage, 'input_tokens_details'):
        input_details = usage.input_tokens_details
        if input_details and isinstance(input_details, dict):
            attributes.update(_extract_attributes_from_mapping(
                input_details, 
                RESPONSE_USAGE_DETAILS_ATTRIBUTES))
        else:
            logger.debug(f"[agentops.instrumentation.openai_agents] '{input_details}' is not a recognized input details type.")
    
    # output_tokens_details is an `OutputTokensDetails` object
    output_details = usage.output_tokens_details
    if output_details and isinstance(output_details, OutputTokensDetails):
        attributes.update(_extract_attributes_from_mapping(
            output_details.__dict__, 
            RESPONSE_USAGE_DETAILS_ATTRIBUTES))
    else:
        logger.debug(f"[agentops.instrumentation.openai_agents] '{output_details}' is not a recognized output details type.")
    
    return attributes


def get_response_reasoning_attributes(reasoning: 'Reasoning') -> AttributeMap:
    """Handles interpretation of an openai Reasoning object."""
    # Reasoning(
    #    effort='medium', 
    #    generate_summary=None, 
    # )
    return _extract_attributes_from_mapping(
        reasoning.__dict__, 
        RESPONSE_REASONING_ATTRIBUTES)

