"""Chat attribute extraction for Google Generative AI instrumentation."""

from typing import Dict, Any, Optional, Tuple

from agentops.logging import logger
from agentops.semconv import SpanAttributes, LLMRequestTypeValues, MessageAttributes
from agentops.instrumentation.common.attributes import AttributeMap
from agentops.instrumentation.google_generativeai.attributes.common import (
    extract_request_attributes,
    get_common_instrumentation_attributes,
)
from agentops.instrumentation.google_generativeai.attributes.model import (
    _extract_content_from_prompt,
    _set_response_attributes,
)


def _extract_message_content(message: Any) -> str:
    """Extract text content from a chat message.

    Handles the various message formats in the Gemini chat API.

    Args:
        message: The message to extract content from

    Returns:
        Extracted text as a string
    """
    if isinstance(message, str):
        return message

    if isinstance(message, dict):
        if "content" in message:
            return _extract_content_from_prompt(message["content"])
        if "text" in message:
            return message["text"]

    if hasattr(message, "content"):
        return _extract_content_from_prompt(message.content)

    if hasattr(message, "text"):
        return message.text

    return ""


def _set_chat_history_attributes(attributes: AttributeMap, args: Tuple, kwargs: Dict[str, Any]) -> None:
    """Extract and set chat history attributes from the request.

    Args:
        attributes: The attribute dictionary to update
        args: Positional arguments to the method
        kwargs: Keyword arguments to the method
    """
    messages = []
    if "message" in kwargs:
        messages = [kwargs["message"]]
    elif args and len(args) > 0:
        messages = [args[0]]
    elif "messages" in kwargs:
        messages = kwargs["messages"]

    if not messages:
        return

    for i, message in enumerate(messages):
        try:
            content = _extract_message_content(message)
            if content:
                role = "user"

                if isinstance(message, dict) and "role" in message:
                    role = message["role"]
                elif hasattr(message, "role"):
                    role = message.role

                attributes[MessageAttributes.PROMPT_CONTENT.format(i=i)] = content
                attributes[MessageAttributes.PROMPT_ROLE.format(i=i)] = role
        except Exception as e:
            logger.debug(f"Error extracting chat message at index {i}: {e}")


def get_chat_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict[str, Any]] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract attributes for chat session methods.

    This function handles attribute extraction for chat session operations,
    particularly the send_message method.

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

    chat_session = None
    if args and len(args) >= 1:
        chat_session = args[0]

    if chat_session and hasattr(chat_session, "model"):
        if isinstance(chat_session.model, str):
            attributes[SpanAttributes.LLM_REQUEST_MODEL] = chat_session.model
        elif hasattr(chat_session.model, "name"):
            attributes[SpanAttributes.LLM_REQUEST_MODEL] = chat_session.model.name

    if args or kwargs:
        _set_chat_history_attributes(attributes, args or (), kwargs or {})

    if return_value is not None:
        _set_response_attributes(attributes, return_value)

    return attributes
