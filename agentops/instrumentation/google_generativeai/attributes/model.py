"""Model attribute extraction for Google Generative AI instrumentation."""

from typing import Dict, Any, Optional, Tuple

from agentops.logging import logger
from agentops.semconv import SpanAttributes, LLMRequestTypeValues, MessageAttributes
from agentops.instrumentation.common.attributes import AttributeMap
from agentops.instrumentation.google_generativeai.attributes.common import (
    extract_request_attributes,
    get_common_instrumentation_attributes,
)


def _extract_content_from_prompt(content: Any) -> str:
    """Extract prompt text from content.

    Handles the various content formats that Google's Generative AI SDK accepts,
    including strings, ContentDict, lists of parts, etc.

    Args:
        content: The content object to extract text from

    Returns:
        Extracted text as a string
    """
    # Direct string case
    if isinstance(content, str):
        return content

    # Lists of parts/content
    if isinstance(content, list):
        text = ""
        for item in content:
            if isinstance(item, str):
                text += item + "\n"
            elif isinstance(item, dict) and "text" in item:
                text += item["text"] + "\n"
            elif hasattr(item, "text"):
                text += item.text + "\n"
            # Handle content as a list with mixed types
            elif hasattr(item, "parts"):
                parts = item.parts
                for part in parts:
                    if isinstance(part, str):
                        text += part + "\n"
                    elif hasattr(part, "text"):
                        text += part.text + "\n"
        return text

    # Dict with text key
    if isinstance(content, dict) and "text" in content:
        return content["text"]

    # Content object with text attribute
    if hasattr(content, "text"):
        return content.text

    # Content object with parts attribute
    if hasattr(content, "parts"):
        text = ""
        for part in content.parts:
            if isinstance(part, str):
                text += part + "\n"
            elif hasattr(part, "text"):
                text += part.text + "\n"
        return text

    # Other object types - try to convert to string
    try:
        return str(content)
    except Exception:
        return ""


def _set_prompt_attributes(attributes: AttributeMap, args: Tuple, kwargs: Dict[str, Any]) -> None:
    """Extract and set prompt attributes from the request.

    Respects privacy controls and handles the various ways prompts can be specified
    in the Google Generative AI API.

    Args:
        attributes: The attribute dictionary to update
        args: Positional arguments to the method
        kwargs: Keyword arguments to the method
    """

    content = None
    if args and len(args) > 0:
        content = args[0]
    elif "contents" in kwargs:
        content = kwargs["contents"]
    elif "content" in kwargs:
        content = kwargs["content"]

    if content is None:
        return

    if isinstance(content, list):
        for i, item in enumerate(content):
            try:
                extracted_text = _extract_content_from_prompt(item)
                if extracted_text:
                    attributes[MessageAttributes.PROMPT_CONTENT.format(i=i)] = extracted_text
                    role = "user"
                    if isinstance(item, dict) and "role" in item:
                        role = item["role"]
                    elif hasattr(item, "role"):
                        role = item.role
                    attributes[MessageAttributes.PROMPT_ROLE.format(i=i)] = role
            except Exception as e:
                logger.debug(f"Error extracting prompt content at index {i}: {e}")
    else:
        try:
            extracted_text = _extract_content_from_prompt(content)
            if extracted_text:
                attributes[MessageAttributes.PROMPT_CONTENT.format(i=0)] = extracted_text
                attributes[MessageAttributes.PROMPT_ROLE.format(i=0)] = "user"
        except Exception as e:
            logger.debug(f"Error extracting prompt content: {e}")


def _set_response_attributes(attributes: AttributeMap, response: Any) -> None:
    """Extract and set response attributes from the completion response.

    Args:
        attributes: The attribute dictionary to update
        response: The response from the API
    """
    if response is None:
        return

    if hasattr(response, "model"):
        attributes[SpanAttributes.LLM_RESPONSE_MODEL] = response.model

    if hasattr(response, "usage_metadata"):
        usage = response.usage_metadata
        if hasattr(usage, "prompt_token_count"):
            attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = usage.prompt_token_count
        if hasattr(usage, "candidates_token_count"):
            attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = usage.candidates_token_count
        if hasattr(usage, "total_token_count"):
            attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = usage.total_token_count

    try:
        if hasattr(response, "text"):
            attributes[MessageAttributes.COMPLETION_CONTENT.format(i=0)] = response.text
            attributes[MessageAttributes.COMPLETION_ROLE.format(i=0)] = "assistant"
        elif hasattr(response, "candidates"):
            # List of candidates
            for i, candidate in enumerate(response.candidates):
                if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
                    parts = candidate.content.parts
                    text = ""
                    for part in parts:
                        if isinstance(part, str):
                            text += part
                        elif hasattr(part, "text"):
                            text += part.text

                    attributes[MessageAttributes.COMPLETION_CONTENT.format(i=i)] = text
                    attributes[MessageAttributes.COMPLETION_ROLE.format(i=i)] = "assistant"

                if hasattr(candidate, "finish_reason"):
                    attributes[MessageAttributes.COMPLETION_FINISH_REASON.format(i=i)] = candidate.finish_reason
    except Exception as e:
        logger.debug(f"Error extracting completion content: {e}")


def get_model_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict[str, Any]] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract attributes for GenerativeModel methods.

    This function handles attribute extraction for the general model operations,
    focusing on the common parameters and pattern shared by multiple methods.

    Args:
        args: Positional arguments to the method
        kwargs: Keyword arguments to the method
        return_value: Return value from the method

    Returns:
        Dictionary of extracted attributes
    """
    attributes = get_common_instrumentation_attributes()
    attributes[SpanAttributes.LLM_SYSTEM] = "Gemini"
    attributes[SpanAttributes.LLM_REQUEST_TYPE] = LLMRequestTypeValues.CHAT.value

    if kwargs:
        kwargs_attributes = extract_request_attributes(kwargs)
        attributes.update(kwargs_attributes)

    if args or kwargs:
        _set_prompt_attributes(attributes, args or (), kwargs or {})

    if return_value is not None:
        _set_response_attributes(attributes, return_value)

    return attributes


def get_generate_content_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict[str, Any]] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract attributes for the generate_content method.

    This specialized extractor handles the generate_content method,
    which is the primary way to interact with Gemini models.

    Args:
        args: Positional arguments to the method
        kwargs: Keyword arguments to the method
        return_value: Return value from the method

    Returns:
        Dictionary of extracted attributes
    """
    return get_model_attributes(args, kwargs, return_value)


def get_token_counting_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict[str, Any]] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract attributes for token counting operations.

    This specialized extractor handles token counting operations.

    Args:
        args: Positional arguments to the method
        kwargs: Keyword arguments to the method
        return_value: Return value from the method

    Returns:
        Dictionary of extracted attributes
    """
    attributes = get_common_instrumentation_attributes()
    attributes[SpanAttributes.LLM_SYSTEM] = "Gemini"
    attributes[SpanAttributes.LLM_REQUEST_TYPE] = "token_count"

    # Process kwargs if available
    if kwargs:
        kwargs_attributes = extract_request_attributes(kwargs)
        attributes.update(kwargs_attributes)

    # Set token count from response
    if return_value is not None:
        if hasattr(return_value, "total_tokens"):
            attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = return_value.total_tokens
        elif hasattr(return_value, "total_token_count"):
            attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = return_value.total_token_count

    return attributes


def get_stream_attributes(stream: Any) -> AttributeMap:
    """Extract attributes from a stream object.

    Args:
        stream: The stream object to extract attributes from

    Returns:
        Dictionary of extracted attributes
    """
    attributes = {}

    if hasattr(stream, "model"):
        attributes[SpanAttributes.LLM_RESPONSE_MODEL] = stream.model

    return attributes
