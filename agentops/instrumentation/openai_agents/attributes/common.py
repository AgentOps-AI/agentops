"""Common utilities and constants for attribute processing.

This module contains shared constants, attribute mappings, and utility functions for processing
trace and span attributes in OpenAI Agents instrumentation. It provides the core functionality
for extracting and formatting attributes according to OpenTelemetry semantic conventions.
"""

from typing import Any
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

# Import full_prompt_contextvar from the new context module
from ..context import full_prompt_contextvar, agent_name_contextvar, agent_handoffs_contextvar
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


# Attribute mapping for FunctionSpanData - Corrected for Tool Semantics
# FunctionSpanData has: name (str), input (Any), output (Any), from_agent (str, optional)
CORRECTED_FUNCTION_TOOL_ATTRIBUTES: AttributeMap = {
    ToolAttributes.TOOL_NAME: "name",
    ToolAttributes.TOOL_PARAMETERS: "input",  # Will be serialized
    ToolAttributes.TOOL_RESULT: "output",  # Will be serialized
    # 'from_agent' could be mapped to a custom attribute if needed, or ignored for pure tool spans
    # For now, let's focus on standard tool attributes.
    # AgentAttributes.FROM_AGENT: "from_agent", # Example if we wanted to keep it
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
    WorkflowAttributes.WORKFLOW_INPUT: "input",
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

from typing import List, Dict, Optional  # Ensure these are imported if not already at the top

# (Make sure logger, safe_serialize, MessageAttributes are imported at the top of the file)


def _get_llm_messages_attributes(messages: Optional[List[Dict]], attribute_base: str) -> AttributeMap:
    """
    Extracts attributes from a list of message dictionaries (e.g., prompts or completions).
    Uses the attribute_base to format the specific attribute keys.
    """
    attributes: AttributeMap = {}
    if not messages:
        logger.debug(
            f"[_get_llm_messages_attributes] No messages provided for base: {attribute_base}. Returning empty attributes."
        )
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
    # attributes = _extract_attributes_from_mapping(span_data, AGENT_SPAN_ATTRIBUTES) # We will set attributes more selectively
    attributes = {}  # Start with an empty dict
    attributes.update(get_common_attributes())  # Get common OTel/AgentOps attributes

    # Set AGENTOPS_SPAN_KIND to 'agent'
    attributes[SpanAttributes.AGENTOPS_SPAN_KIND] = AgentOpsSpanKindValues.AGENT.value
    logger.debug(
        f"[get_agent_span_attributes] Set AGENTOPS_SPAN_KIND to '{AgentOpsSpanKindValues.AGENT.value}' for AgentSpanData id: {getattr(span_data, 'id', 'N/A')}"
    )

    # Get agent name from contextvar (set by instrumentor wrapper)
    ctx_agent_name = agent_name_contextvar.get()
    if ctx_agent_name:
        attributes[AgentAttributes.AGENT_NAME] = ctx_agent_name
        logger.debug(f"[get_agent_span_attributes] Set AGENT_NAME from contextvar: {ctx_agent_name}")
    elif hasattr(span_data, "name") and span_data.name:  # Fallback to span_data.name if contextvar is not set
        attributes[AgentAttributes.AGENT_NAME] = str(span_data.name)
        logger.debug(f"[get_agent_span_attributes] Set AGENT_NAME from span_data.name: {str(span_data.name)}")

    # Get simplified handoffs from contextvar (set by instrumentor wrapper)
    ctx_handoffs = agent_handoffs_contextvar.get()
    if ctx_handoffs:
        attributes[AgentAttributes.HANDOFFS] = safe_serialize(ctx_handoffs)  # Ensure it's a JSON string array
        logger.debug(f"[get_agent_span_attributes] Set HANDOFFS from contextvar: {safe_serialize(ctx_handoffs)}")
    elif (
        hasattr(span_data, "handoffs") and span_data.handoffs
    ):  # Fallback for safety, though contextvar should be primary
        # This fallback might re-introduce complex objects if not careful,
        # but contextvar is the intended source for the simplified list.
        attributes[AgentAttributes.HANDOFFS] = safe_serialize(span_data.handoffs)
        logger.debug(
            f"[get_agent_span_attributes] Set HANDOFFS from span_data.handoffs: {safe_serialize(span_data.handoffs)}"
        )

    # Selectively add other relevant attributes from AgentSpanData if needed, avoiding LLM details
    if hasattr(span_data, "input") and span_data.input is not None:
        # Avoid setting detailed prompt input here. If a general workflow input is desired, use a non-LLM semconv.
        # For now, let's assume WORKFLOW_INPUT is too generic and might contain prompts.
        # attributes[WorkflowAttributes.WORKFLOW_INPUT] = safe_serialize(span_data.input)
        pass

    if hasattr(span_data, "output") and span_data.output is not None:
        # Similar to input, avoid detailed LLM output.
        # attributes[WorkflowAttributes.FINAL_OUTPUT] = safe_serialize(span_data.output)
        pass

    if hasattr(span_data, "tools") and span_data.tools:
        # Serialize tools if they are simple list of strings or basic structures
        attributes[AgentAttributes.AGENT_TOOLS] = safe_serialize([str(getattr(t, "name", t)) for t in span_data.tools])

    logger.debug(
        f"[get_agent_span_attributes] Final attributes for AgentSpanData id {getattr(span_data, 'id', 'N/A')}: {safe_serialize(attributes)}"
    )
    return attributes


def get_function_span_attributes(span_data: Any) -> AttributeMap:
    """Extract attributes from a FunctionSpanData object.

    Functions are requests made to the `openai.functions` endpoint.

    Args:
        span_data: The FunctionSpanData object

    Returns:
        Dictionary of attributes for function span
    """
    attributes = _extract_attributes_from_mapping(span_data, CORRECTED_FUNCTION_TOOL_ATTRIBUTES)
    attributes.update(get_common_attributes())
    attributes[SpanAttributes.AGENTOPS_SPAN_KIND] = AgentOpsSpanKindValues.TOOL.value

    # Determine tool status based on presence of error in span_data (if available) or assume success
    # The main SDK's Span object has an 'error' field. If span_data itself doesn't,
    # this status might be better set by the exporter which has access to the full SDK Span.
    # For now, assuming success if no error attribute is directly on span_data.
    # A more robust way would be to check the OTel span's status if this handler is called *after* error processing.
    if hasattr(span_data, "error") and span_data.error:
        attributes[ToolAttributes.TOOL_STATUS] = ToolStatus.FAILED.value
    else:
        # This might be premature if output isn't available yet (on_span_start)
        # but the exporter handles separate start/end, so this is for the full attribute set.
        if hasattr(span_data, "output") and span_data.output is not None:
            attributes[ToolAttributes.TOOL_STATUS] = ToolStatus.SUCCEEDED.value
        else:
            # If called on start, or if output is None without error, it's executing or status unknown yet.
            # The exporter should ideally set this based on the OTel span status later.
            # For now, we won't set a default status here if output is not yet available.
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
    # Get basic attributes from mapping
    attributes = _extract_attributes_from_mapping(span_data, RESPONSE_SPAN_ATTRIBUTES)
    attributes.update(get_common_attributes())

    prompt_attributes_set = False

    # Read full prompt from contextvar (set by instrumentor's wrapper)
    full_prompt_from_context = full_prompt_contextvar.get()
    if full_prompt_from_context:
        logger.debug(
            f"[get_response_span_attributes] Found full_prompt_from_context: {safe_serialize(full_prompt_from_context)}"
        )
        attributes.update(_get_llm_messages_attributes(full_prompt_from_context, "gen_ai.prompt"))
        prompt_attributes_set = True
    else:
        logger.debug("[get_response_span_attributes] full_prompt_contextvar is None.")
        # Fallback to SDK's request_messages if contextvar wasn't available or didn't have prompt
        if (
            span_data.response
            and hasattr(span_data.response, "request_messages")
            and span_data.response.request_messages
        ):
            prompt_messages_from_sdk = span_data.response.request_messages
            logger.debug(
                f"[get_response_span_attributes] Using agents.Response.request_messages: {safe_serialize(prompt_messages_from_sdk)}"
            )
            attributes.update(_get_llm_messages_attributes(prompt_messages_from_sdk, "gen_ai.prompt"))
            prompt_attributes_set = True
        else:
            logger.debug(
                "[get_response_span_attributes] No prompt source: neither contextvar nor SDK request_messages available/sufficient."
            )

    # Process response (completion, usage, model etc.) using the existing get_response_response_attributes
    # This function handles the `span_data.response` object which is an `agents.Response`
    if span_data.response:
        # get_response_response_attributes from openai instrumentation expects an OpenAIObject-like response.
        # We need to ensure it can handle agents.Response or adapt.
        # For now, let's assume it primarily extracts completion and usage, and we've handled prompt.

        # Call the original function to get completion, usage, model, etc.
        # It might also try to set prompt attributes, which we might need to reconcile.
        openai_style_response_attrs = get_response_response_attributes(span_data.response)

        # If we've already set prompt attributes from our preferred source (wrapper context),
        # remove any prompt attributes that get_response_response_attributes might have set,
        # to avoid conflicts or overwriting with potentially less complete data.
        if prompt_attributes_set:
            keys_to_remove = [
                k for k in openai_style_response_attrs if k.startswith("gen_ai.prompt")
            ]  # e.g. "gen_ai.prompt"
            if keys_to_remove:
                for key in keys_to_remove:
                    if key in openai_style_response_attrs:  # Check if key exists before deleting
                        del openai_style_response_attrs[key]

        # Remove gen_ai.request.tools if present, as it's not appropriate for the LLM response span itself
        # The LLM span should reflect the LLM's output (completion, tool_calls selected), not the definition of tools it was given.
        if "gen_ai.request.tools" in openai_style_response_attrs:
            del openai_style_response_attrs["gen_ai.request.tools"]

        attributes.update(openai_style_response_attrs)

    # Ensure LLM span kind is set
    attributes[SpanAttributes.AGENTOPS_SPAN_KIND] = AgentOpsSpanKindValues.LLM.value
    logger.debug(
        f"[get_response_span_attributes] Set AGENTOPS_SPAN_KIND to '{AgentOpsSpanKindValues.LLM.value}' for span_data.id: {getattr(span_data, 'id', 'N/A')}"
    )
    return attributes


def get_generation_span_attributes(span_data: Any) -> AttributeMap:
    """Extract attributes from a GenerationSpanData object.

    Generations are requests made to the `openai.completions` endpoint.

    # TODO this has not been extensively tested yet as there is a flag that needs ot be set to use the
    # completions API with the Agents SDK.
    # We can enable chat.completions API by calling:
    # `from agents import set_default_openai_api`
    # `set_default_openai_api("chat_completions")`

    Args:
        span_data: The GenerationSpanData object

    Returns:
        Dictionary of attributes for generation span
    """
    logger.debug(
        f"[get_generation_span_attributes] Called for span_data.id: {getattr(span_data, 'id', 'N/A')}, name: {getattr(span_data, 'name', 'N/A')}, type: {span_data.__class__.__name__}"
    )
    attributes = _extract_attributes_from_mapping(
        span_data, GENERATION_SPAN_ATTRIBUTES
    )  # This might set gen_ai.prompt from span_data.input
    attributes.update(get_common_attributes())

    prompt_attributes_set = False
    # Read full prompt from contextvar (set by instrumentor's wrapper)
    full_prompt_from_context = full_prompt_contextvar.get()

    if full_prompt_from_context:
        logger.debug(
            f"[get_generation_span_attributes] Found full_prompt_from_context: {safe_serialize(full_prompt_from_context)}"
        )
        # Clear any prompt set by _extract_attributes_from_mapping from span_data.input
        prompt_keys_to_clear = [k for k in attributes if k.startswith("gen_ai.prompt")]
        if SpanAttributes.LLM_PROMPTS in attributes:
            prompt_keys_to_clear.append(SpanAttributes.LLM_PROMPTS)
        for key in set(prompt_keys_to_clear):
            if key in attributes:
                del attributes[key]

        attributes.update(_get_llm_messages_attributes(full_prompt_from_context, "gen_ai.prompt"))
        prompt_attributes_set = True
    elif SpanAttributes.LLM_PROMPTS in attributes:  # Fallback to span_data.input if contextvar is empty
        logger.debug(
            "[get_generation_span_attributes] full_prompt_contextvar is None. Using LLM_PROMPTS from span_data.input."
        )
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
            prompt_attributes_set = True
        else:
            logger.debug(
                "[get_generation_span_attributes] No prompt data from span_data.input or it was not formattable."
            )
    else:
        logger.debug(
            "[get_generation_span_attributes] No prompt source: contextvar is None and no LLM_PROMPTS in attributes from span_data.input."
        )

    if span_data.model:
        attributes.update(get_model_attributes(span_data.model))

    # Process output for GenerationSpanData if available
    if span_data.output:
        attributes.update(get_generation_output_attributes(span_data.output))

    # Add model config attributes if present
    if span_data.model_config:
        attributes.update(get_model_config_attributes(span_data.model_config))

    # Ensure LLM span kind is set
    attributes[SpanAttributes.AGENTOPS_SPAN_KIND] = AgentOpsSpanKindValues.LLM.value
    logger.debug(
        f"[get_generation_span_attributes] Set AGENTOPS_SPAN_KIND to '{AgentOpsSpanKindValues.LLM.value}' for span_data.id: {getattr(span_data, 'id', 'N/A')}. Current attributes include agentops.span.kind: {attributes.get(SpanAttributes.AGENTOPS_SPAN_KIND)}"
    )
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
