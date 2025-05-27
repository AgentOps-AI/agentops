"""Common utilities and constants for attribute processing.

This module contains shared constants, attribute mappings, and utility functions for processing
trace and span attributes in OpenAI Agents instrumentation. It provides the core functionality
for extracting and formatting attributes according to OpenTelemetry semantic conventions.
"""

from typing import Any, List, Dict, Optional
from agentops.logging import logger
from agentops.semconv import (
    AgentAttributes,
    WorkflowAttributes,
    SpanAttributes,
    InstrumentationAttributes,
    ToolAttributes,
    AgentOpsSpanKindValues,
    ToolStatus,
)
from agentops.helpers import safe_serialize  # Import safe_serialize

from agentops.instrumentation.common import AttributeMap, _extract_attributes_from_mapping
from agentops.instrumentation.common.attributes import get_common_attributes
from agentops.instrumentation.common.objects import get_uploaded_object_attributes
from agentops.instrumentation.openai.attributes.response import get_response_response_attributes
from agentops.instrumentation.openai_agents import LIBRARY_NAME, LIBRARY_VERSION

from agentops.instrumentation.openai_agents.attributes.model import (
    get_model_attributes,
    get_model_config_attributes,
)
from agentops.instrumentation.openai_agents.attributes.completion import get_generation_output_attributes


# Attribute mapping for AgentSpanData
AGENT_SPAN_ATTRIBUTES: AttributeMap = {
    AgentAttributes.AGENT_NAME: "name",
    AgentAttributes.AGENT_TOOLS: "tools",
    AgentAttributes.HANDOFFS: "handoffs",
    WorkflowAttributes.WORKFLOW_INPUT: "input",
    WorkflowAttributes.FINAL_OUTPUT: "output",
}


# Attribute mapping for FunctionSpanData
FUNCTION_TOOL_ATTRIBUTES: AttributeMap = {
    ToolAttributes.TOOL_NAME: "name",
    ToolAttributes.TOOL_PARAMETERS: "input",
    ToolAttributes.TOOL_RESULT: "output",
    # AgentAttributes.AGENT_NAME: "name",
    AgentAttributes.FROM_AGENT: "from_agent",
}


# Attribute mapping for HandoffSpanData
HANDOFF_SPAN_ATTRIBUTES: AttributeMap = {
    AgentAttributes.FROM_AGENT: "from_agent",
    AgentAttributes.TO_AGENT: "to_agent",
}


# Attribute mapping for GenerationSpanData
GENERATION_SPAN_ATTRIBUTES: AttributeMap = {
    SpanAttributes.LLM_PROMPTS: "input",
}


# Attribute mapping for ResponseSpanData
RESPONSE_SPAN_ATTRIBUTES: AttributeMap = {
    # Don't map input here as it causes double serialization
    # We handle prompts manually in get_response_span_attributes
    SpanAttributes.LLM_RESPONSE_MODEL: "model",
}


# Attribute mapping for TranscriptionSpanData
TRANSCRIPTION_SPAN_ATTRIBUTES: AttributeMap = {
    # `input` and `input_format` are handled below
    WorkflowAttributes.WORKFLOW_OUTPUT: "output",
}


# Attribute mapping for SpeechSpanData
SPEECH_SPAN_ATTRIBUTES: AttributeMap = {
    WorkflowAttributes.WORKFLOW_INPUT: "input",
    # `output` and `output_format` are handled below
    # TODO `first_content_at` is not converted
}


# Attribute mapping for SpeechGroupSpanData
SPEECH_GROUP_SPAN_ATTRIBUTES: AttributeMap = {
    WorkflowAttributes.WORKFLOW_INPUT: "input",
}


def _get_llm_messages_attributes(messages: Optional[List[Dict]], attribute_base: str) -> AttributeMap:
    """
    Extracts attributes from a list of message dictionaries (e.g., prompts or completions).
    Uses the attribute_base to format the specific attribute keys.
    """
    attributes: AttributeMap = {}
    if not messages:
        return attributes
    if not isinstance(messages, list):
        logger.warning(
            f"[_get_llm_messages_attributes] Expected a list of messages for base '{attribute_base}', got {type(messages)}. Value: {safe_serialize(messages)}. Returning empty."
        )
        return attributes

    for i, msg_dict in enumerate(messages):
        if isinstance(msg_dict, dict):
            role = msg_dict.get("role")
            content = msg_dict.get("content")
            name = msg_dict.get("name")  # For named messages if ever used
            tool_calls = msg_dict.get("tool_calls")  # For assistant messages with tool calls
            tool_call_id = msg_dict.get("tool_call_id")  # For tool_call_output messages

            # Common role and content
            if role:
                attributes[f"{attribute_base}.{i}.role"] = str(role)
            if content is not None:  # Ensure content can be an empty string but not None without being set
                attributes[f"{attribute_base}.{i}.content"] = safe_serialize(content)

            # Optional name for some roles
            if name:
                attributes[f"{attribute_base}.{i}.name"] = str(name)

            # Tool calls (specific to assistant messages)
            if tool_calls and isinstance(tool_calls, list):
                for tc_idx, tc_dict in enumerate(tool_calls):
                    if isinstance(tc_dict, dict):
                        tc_id = tc_dict.get("id")
                        tc_type = tc_dict.get("type")  # e.g., "function"
                        tc_function_data = tc_dict.get("function")

                        if tc_function_data and isinstance(tc_function_data, dict):
                            tc_func_name = tc_function_data.get("name")
                            tc_func_args = tc_function_data.get("arguments")

                            base_tool_call_key_formatted = f"{attribute_base}.{i}.tool_calls.{tc_idx}"
                            if tc_id:
                                attributes[f"{base_tool_call_key_formatted}.id"] = str(tc_id)
                            if tc_type:
                                attributes[f"{base_tool_call_key_formatted}.type"] = str(tc_type)
                            if tc_func_name:
                                attributes[f"{base_tool_call_key_formatted}.function.name"] = str(tc_func_name)
                            if tc_func_args is not None:  # Arguments can be an empty string
                                attributes[f"{base_tool_call_key_formatted}.function.arguments"] = safe_serialize(
                                    tc_func_args
                                )

            # Tool call ID (specific to tool_call_output messages)
            if tool_call_id:  # This is for the result of a tool call
                attributes[f"{attribute_base}.{i}.tool_call_id"] = str(tool_call_id)
        else:
            # If a message is not a dict, serialize its representation
            attributes[f"{attribute_base}.{i}.content"] = safe_serialize(msg_dict)

    return attributes


def get_common_instrumentation_attributes() -> AttributeMap:
    """Get common instrumentation attributes for the OpenAI Agents instrumentation.

    This combines the generic AgentOps attributes with OpenAI Agents specific library attributes.

    Returns:
        Dictionary of common instrumentation attributes
    """
    attributes = get_common_attributes()
    attributes.update(
        {
            InstrumentationAttributes.LIBRARY_NAME: LIBRARY_NAME,
            InstrumentationAttributes.LIBRARY_VERSION: LIBRARY_VERSION,
        }
    )
    return attributes


def get_agent_span_attributes(span_data: Any) -> AttributeMap:
    """Extract attributes from an AgentSpanData object.

    Agents are requests made to the `openai.agents` endpoint.

    Args:
        span_data: The AgentSpanData object

    Returns:
        Dictionary of attributes for agent span
    """
    attributes = {}  # Start with an empty dict
    attributes.update(get_common_attributes())  # Get common OTel/AgentOps attributes

    attributes[SpanAttributes.AGENTOPS_SPAN_KIND] = AgentOpsSpanKindValues.AGENT.value

    # Get agent name directly from span_data
    if hasattr(span_data, "name") and span_data.name:
        attributes[AgentAttributes.AGENT_NAME] = str(span_data.name)

    # Get handoffs directly from span_data
    if hasattr(span_data, "handoffs") and span_data.handoffs:
        attributes[AgentAttributes.HANDOFFS] = safe_serialize(span_data.handoffs)

    if hasattr(span_data, "tools") and span_data.tools:
        attributes[AgentAttributes.AGENT_TOOLS] = safe_serialize([str(getattr(t, "name", t)) for t in span_data.tools])

    return attributes


def get_function_span_attributes(span_data: Any) -> AttributeMap:
    """Extract attributes from a FunctionSpanData object.

    Functions are requests made to the `openai.functions` endpoint.

    Args:
        span_data: The FunctionSpanData object

    Returns:
        Dictionary of attributes for function span
    """
    attributes = _extract_attributes_from_mapping(span_data, FUNCTION_TOOL_ATTRIBUTES)
    attributes.update(get_common_attributes())
    attributes[SpanAttributes.AGENTOPS_SPAN_KIND] = AgentOpsSpanKindValues.TOOL.value

    # Determine tool status based on presence of error
    if hasattr(span_data, "error") and span_data.error:
        attributes[ToolAttributes.TOOL_STATUS] = ToolStatus.FAILED.value
    else:
        if hasattr(span_data, "output") and span_data.output is not None:
            attributes[ToolAttributes.TOOL_STATUS] = ToolStatus.SUCCEEDED.value
        else:
            # Status will be set by exporter based on span lifecycle
            pass

    # If from_agent is available on span_data, add it.
    if hasattr(span_data, "from_agent") and span_data.from_agent:
        attributes[f"{AgentAttributes.AGENT}.calling_tool.name"] = str(span_data.from_agent)

    return attributes


def get_handoff_span_attributes(span_data: Any) -> AttributeMap:
    """Extract attributes from a HandoffSpanData object.

    Handoffs are requests made to the `openai.handoffs` endpoint.

    Args:
        span_data: The HandoffSpanData object

    Returns:
        Dictionary of attributes for handoff span
    """
    attributes = _extract_attributes_from_mapping(span_data, HANDOFF_SPAN_ATTRIBUTES)
    attributes.update(get_common_attributes())

    return attributes


def get_response_span_attributes(span_data: Any) -> AttributeMap:
    """Extract attributes from a ResponseSpanData object with full LLM response processing.

    Responses are requests made to the `openai.responses` endpoint.

    This function extracts not just the basic input/response mapping but also processes
    the rich response object to extract LLM-specific attributes like token usage,
    model information, content, etc.

    TODO tool calls arrive from this span type; need to figure out why that is.

    Args:
        span_data: The ResponseSpanData object

    Returns:
        Dictionary of attributes for response span
    """
    # Debug logging
    import json
    print(f"\n[DEBUG] get_response_span_attributes called")
    print(f"[DEBUG] span_data type: {type(span_data)}")
    print(f"[DEBUG] span_data attributes: {[attr for attr in dir(span_data) if not attr.startswith('_')]}")
    
    # Check what's in span_data.input
    if hasattr(span_data, "input"):
        print(f"[DEBUG] span_data.input type: {type(span_data.input)}")
        try:
            print(f"[DEBUG] span_data.input content: {json.dumps(span_data.input, indent=2) if span_data.input else 'None'}")
        except:
            print(f"[DEBUG] span_data.input content (repr): {repr(span_data.input)}")
    
    # Check for response and instructions
    if hasattr(span_data, "response") and span_data.response:
        print(f"[DEBUG] span_data.response type: {type(span_data.response)}")
        if hasattr(span_data.response, "instructions"):
            print(f"[DEBUG] span_data.response.instructions: {span_data.response.instructions}")
    
    # Get basic attributes from mapping
    attributes = _extract_attributes_from_mapping(span_data, RESPONSE_SPAN_ATTRIBUTES)
    attributes.update(get_common_attributes())

    # Build complete prompt list from system instructions and conversation history
    prompt_messages = []
    
    # Add system instruction as first message if available
    if span_data.response and hasattr(span_data.response, "instructions") and span_data.response.instructions:
        prompt_messages.append({
            "role": "system",
            "content": span_data.response.instructions
        })
        print(f"[DEBUG] Added system message from instructions")
    
    # Add conversation history from span_data.input
    if hasattr(span_data, "input") and span_data.input:
        if isinstance(span_data.input, list):
            for i, msg in enumerate(span_data.input):
                print(f"[DEBUG] Processing message {i}: type={type(msg)}")
                if isinstance(msg, dict):
                    role = msg.get("role")
                    content = msg.get("content")
                    print(f"[DEBUG] Message {i}: role={role}, content type={type(content)}")
                    
                    # Handle different content formats
                    if role and content is not None:
                        # If content is a string, use it directly
                        if isinstance(content, str):
                            prompt_messages.append({
                                "role": role,
                                "content": content
                            })
                        # If content is a list (complex assistant message), extract text
                        elif isinstance(content, list):
                            text_parts = []
                            for item in content:
                                if isinstance(item, dict):
                                    # Handle output_text type
                                    if item.get("type") == "output_text":
                                        text_parts.append(item.get("text", ""))
                                    # Handle other text content
                                    elif "text" in item:
                                        text_parts.append(item.get("text", ""))
                                    # Handle annotations with text
                                    elif "annotations" in item and "text" in item:
                                        text_parts.append(item.get("text", ""))
                            
                            if text_parts:
                                prompt_messages.append({
                                    "role": role,
                                    "content": " ".join(text_parts)
                                })
                        # If content is a dict, try to extract text
                        elif isinstance(content, dict):
                            if "text" in content:
                                prompt_messages.append({
                                    "role": role,
                                    "content": content["text"]
                                })
        elif isinstance(span_data.input, str):
            # Single string input - assume it's a user message
            prompt_messages.append({
                "role": "user",
                "content": span_data.input
            })
            print(f"[DEBUG] Added user message from string input")
    
    print(f"[DEBUG] Total prompt_messages: {len(prompt_messages)}")
    for i, msg in enumerate(prompt_messages):
        print(f"[DEBUG] prompt_messages[{i}]: role={msg.get('role')}, content_len={len(str(msg.get('content', '')))}")
    
    # Format prompts using existing function
    if prompt_messages:
        attributes.update(_get_llm_messages_attributes(prompt_messages, "gen_ai.prompt"))

    # Process response attributes
    if span_data.response:
        openai_style_response_attrs = get_response_response_attributes(span_data.response)

        # Remove any prompt attributes from response processing since we handle them above
        keys_to_remove = [k for k in openai_style_response_attrs if k.startswith("gen_ai.prompt")]
        for key in keys_to_remove:
            if key in openai_style_response_attrs:
                del openai_style_response_attrs[key]

        # Remove tool definitions from response attributes
        if "gen_ai.request.tools" in openai_style_response_attrs:
            del openai_style_response_attrs["gen_ai.request.tools"]

        attributes.update(openai_style_response_attrs)

    attributes[SpanAttributes.AGENTOPS_SPAN_KIND] = AgentOpsSpanKindValues.LLM.value
    
    print(f"[DEBUG] Final attributes keys: {list(attributes.keys())}")
    prompt_keys = [k for k in attributes.keys() if k.startswith("gen_ai.prompt")]
    print(f"[DEBUG] Prompt attribute keys: {prompt_keys}")
    
    return attributes


def get_generation_span_attributes(span_data: Any) -> AttributeMap:
    """Extract attributes from a GenerationSpanData object.

    Generations are requests made to the `openai.completions` endpoint.

    Args:
        span_data: The GenerationSpanData object

    Returns:
        Dictionary of attributes for generation span
    """
    attributes = _extract_attributes_from_mapping(
        span_data, GENERATION_SPAN_ATTRIBUTES
    )  # This might set gen_ai.prompt from span_data.input
    attributes.update(get_common_attributes())

    # Process prompt from span_data.input
    if SpanAttributes.LLM_PROMPTS in attributes:
        raw_prompt_input = attributes.pop(SpanAttributes.LLM_PROMPTS)
        formatted_prompt_for_llm = []
        if isinstance(raw_prompt_input, str):
            formatted_prompt_for_llm.append({"role": "user", "content": raw_prompt_input})
        elif isinstance(raw_prompt_input, list):
            temp_formatted_list = []
            all_strings_or_dicts = True
            for item in raw_prompt_input:
                if isinstance(item, str):
                    temp_formatted_list.append({"role": "user", "content": item})
                elif isinstance(item, dict):
                    temp_formatted_list.append(item)
                else:
                    all_strings_or_dicts = False
                    break
            if all_strings_or_dicts:
                formatted_prompt_for_llm = temp_formatted_list
            else:
                logger.warning(
                    f"[get_generation_span_attributes] span_data.input was a list with mixed/unexpected content: {safe_serialize(raw_prompt_input)}"
                )

        if formatted_prompt_for_llm:
            attributes.update(_get_llm_messages_attributes(formatted_prompt_for_llm, "gen_ai.prompt"))

    if span_data.model:
        attributes.update(get_model_attributes(span_data.model))

    # Process output for GenerationSpanData if available
    if span_data.output:
        attributes.update(get_generation_output_attributes(span_data.output))

    # Add model config attributes if present
    if span_data.model_config:
        attributes.update(get_model_config_attributes(span_data.model_config))

    attributes[SpanAttributes.AGENTOPS_SPAN_KIND] = AgentOpsSpanKindValues.LLM.value
    return attributes


def get_transcription_span_attributes(span_data: Any) -> AttributeMap:
    """Extract attributes from a TranscriptionSpanData object.

    This represents a conversion from audio to text.

    Args:
        span_data: The TranscriptionSpanData object
    Returns:
        Dictionary of attributes for transcription span
    """
    from agentops import get_client
    from agentops.client.api.types import UploadedObjectResponse

    client = get_client()

    attributes = _extract_attributes_from_mapping(span_data, TRANSCRIPTION_SPAN_ATTRIBUTES)
    attributes.update(get_common_attributes())

    if span_data.input:
        prefix = WorkflowAttributes.WORKFLOW_INPUT
        uploaded_object: UploadedObjectResponse = client.api.v4.upload_object(span_data.input)
        attributes.update(get_uploaded_object_attributes(uploaded_object, prefix))

    if span_data.model:
        attributes.update(get_model_attributes(span_data.model))

    if span_data.model_config:
        attributes.update(get_model_config_attributes(span_data.model_config))

    return attributes


def get_speech_span_attributes(span_data: Any) -> AttributeMap:
    """Extract attributes from a SpeechSpanData object.

    This represents a conversion from audio to text.

    Args:
        span_data: The SpeechSpanData object

    Returns:
        Dictionary of attributes for speech span
    """
    from agentops import get_client
    from agentops.client.api.types import UploadedObjectResponse

    client = get_client()

    attributes = _extract_attributes_from_mapping(span_data, SPEECH_SPAN_ATTRIBUTES)
    attributes.update(get_common_attributes())

    if span_data.output:
        prefix = WorkflowAttributes.WORKFLOW_OUTPUT
        uploaded_object: UploadedObjectResponse = client.api.v4.upload_object(span_data.output)
        attributes.update(get_uploaded_object_attributes(uploaded_object, prefix))

    if span_data.model:
        attributes.update(get_model_attributes(span_data.model))

    if span_data.model_config:
        attributes.update(get_model_config_attributes(span_data.model_config))

    return attributes


def get_speech_group_span_attributes(span_data: Any) -> AttributeMap:
    """Extract attributes from a SpeechGroupSpanData object.

    This represents a conversion from audio to text.

    Args:
        span_data: The SpeechGroupSpanData object

    Returns:
        Dictionary of attributes for speech group span
    """
    attributes = _extract_attributes_from_mapping(span_data, SPEECH_GROUP_SPAN_ATTRIBUTES)
    attributes.update(get_common_attributes())

    return attributes


def get_span_attributes(span_data: Any) -> AttributeMap:
    """Get attributes for a span based on its type.

    This function centralizes attribute extraction by delegating to type-specific
    getter functions.

    Args:
        span_data: The span data object

    Returns:
        Dictionary of attributes for the span
    """
    span_type = span_data.__class__.__name__

    if span_type == "AgentSpanData":
        attributes = get_agent_span_attributes(span_data)
    elif span_type == "FunctionSpanData":
        attributes = get_function_span_attributes(span_data)
    elif span_type == "GenerationSpanData":
        attributes = get_generation_span_attributes(span_data)
    elif span_type == "HandoffSpanData":
        attributes = get_handoff_span_attributes(span_data)
    elif span_type == "ResponseSpanData":
        attributes = get_response_span_attributes(span_data)
    elif span_type == "TranscriptionSpanData":
        attributes = get_transcription_span_attributes(span_data)
    elif span_type == "SpeechSpanData":
        attributes = get_speech_span_attributes(span_data)
    elif span_type == "SpeechGroupSpanData":
        attributes = get_speech_group_span_attributes(span_data)
    else:
        logger.debug(f"[agentops.instrumentation.openai_agents.attributes] Unknown span type: {span_type}")
        attributes = {}

    return attributes
