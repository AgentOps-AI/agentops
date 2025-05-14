"""Common utilities and constants for attribute processing.

This module contains shared constants, attribute mappings, and utility functions for processing
trace and span attributes in OpenAI Agents instrumentation. It provides the core functionality
for extracting and formatting attributes according to OpenTelemetry semantic conventions.
"""

from typing import Any
from agentops.logging import logger
from agentops.semconv import AgentAttributes, WorkflowAttributes, SpanAttributes, InstrumentationAttributes

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
FUNCTION_SPAN_ATTRIBUTES: AttributeMap = {
    AgentAttributes.AGENT_NAME: "name",
    WorkflowAttributes.WORKFLOW_INPUT: "input",
    WorkflowAttributes.FINAL_OUTPUT: "output",
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
    attributes = _extract_attributes_from_mapping(span_data, AGENT_SPAN_ATTRIBUTES)
    attributes.update(get_common_attributes())

    return attributes


def get_function_span_attributes(span_data: Any) -> AttributeMap:
    """Extract attributes from a FunctionSpanData object.

    Functions are requests made to the `openai.functions` endpoint.

    Args:
        span_data: The FunctionSpanData object

    Returns:
        Dictionary of attributes for function span
    """
    attributes = _extract_attributes_from_mapping(span_data, FUNCTION_SPAN_ATTRIBUTES)
    attributes.update(get_common_attributes())

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

    if span_data.response:
        attributes.update(get_response_response_attributes(span_data.response))

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
    attributes = _extract_attributes_from_mapping(span_data, GENERATION_SPAN_ATTRIBUTES)
    attributes.update(get_common_attributes())

    if span_data.model:
        attributes.update(get_model_attributes(span_data.model))

    # Process output for GenerationSpanData if available
    if span_data.output:
        attributes.update(get_generation_output_attributes(span_data.output))

    # Add model config attributes if present
    if span_data.model_config:
        attributes.update(get_model_config_attributes(span_data.model_config))

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
