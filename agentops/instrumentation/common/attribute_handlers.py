"""Enhanced attribute handling utilities for OpenTelemetry instrumentation.

This module provides advanced utilities for extracting and formatting attributes
from various data sources, including:
- LLM request/response data
- Tool invocations
- Message content
- Token usage metrics
- Error information
"""

from typing import Any, Dict, List, Optional, Callable, Tuple
from functools import wraps

from agentops.instrumentation.common.attributes import AttributeMap, _extract_attributes_from_mapping
from agentops.helpers import safe_serialize
from agentops.semconv import SpanAttributes, MessageAttributes, LLMRequestTypeValues
from agentops.logging import logger


class AttributeExtractor:
    """Base class for attribute extraction with common patterns."""

    @staticmethod
    def extract_safely(
        source: Any,
        attribute_map: AttributeMap,
        prefix: Optional[str] = None,
        serializer: Callable[[Any], str] = safe_serialize,
    ) -> AttributeMap:
        """Safely extract attributes with error handling.

        Args:
            source: The source object to extract from
            attribute_map: Mapping of target to source attributes
            prefix: Optional prefix to add to all keys
            serializer: Function to serialize complex values

        Returns:
            Extracted attributes
        """
        try:
            attributes = _extract_attributes_from_mapping(source, attribute_map)

            if prefix:
                attributes = {f"{prefix}.{k}": v for k, v in attributes.items()}

            return attributes
        except Exception as e:
            logger.debug(f"Error extracting attributes: {e}")
            return {}

    @staticmethod
    def merge_attributes(*attribute_dicts: AttributeMap) -> AttributeMap:
        """Merge multiple attribute dictionaries.

        Args:
            *attribute_dicts: Dictionaries to merge

        Returns:
            Merged attributes
        """
        result = {}
        for attrs in attribute_dicts:
            if attrs:
                result.update(attrs)
        return result


class LLMAttributeHandler:
    """Common attribute handling for LLM requests and responses."""

    # Common request attribute mappings
    REQUEST_ATTRIBUTES: AttributeMap = {
        SpanAttributes.LLM_REQUEST_MODEL: "model",
        SpanAttributes.LLM_REQUEST_MAX_TOKENS: "max_tokens",
        SpanAttributes.LLM_REQUEST_TEMPERATURE: "temperature",
        SpanAttributes.LLM_REQUEST_TOP_P: "top_p",
        SpanAttributes.LLM_REQUEST_TOP_K: "top_k",
        SpanAttributes.LLM_REQUEST_SEED: "seed",
        SpanAttributes.LLM_REQUEST_STOP_SEQUENCES: "stop",
        SpanAttributes.LLM_REQUEST_FREQUENCY_PENALTY: "frequency_penalty",
        SpanAttributes.LLM_REQUEST_PRESENCE_PENALTY: "presence_penalty",
        SpanAttributes.LLM_REQUEST_STREAMING: "stream",
    }

    # Common response attribute mappings
    RESPONSE_ATTRIBUTES: AttributeMap = {
        SpanAttributes.LLM_RESPONSE_MODEL: "model",
        SpanAttributes.LLM_RESPONSE_ID: "id",
        SpanAttributes.LLM_RESPONSE_FINISH_REASON: "finish_reason",
    }

    # Common usage attribute mappings
    USAGE_ATTRIBUTES: AttributeMap = {
        SpanAttributes.LLM_USAGE_PROMPT_TOKENS: "prompt_tokens",
        SpanAttributes.LLM_USAGE_COMPLETION_TOKENS: "completion_tokens",
        SpanAttributes.LLM_USAGE_TOTAL_TOKENS: "total_tokens",
    }

    @classmethod
    def extract_request_attributes(
        cls, kwargs: Dict[str, Any], additional_mappings: Optional[AttributeMap] = None
    ) -> AttributeMap:
        """Extract standard LLM request attributes.

        Args:
            kwargs: Request keyword arguments
            additional_mappings: Provider-specific mappings to include

        Returns:
            Extracted attributes
        """
        # Merge standard and additional mappings
        mappings = cls.REQUEST_ATTRIBUTES.copy()
        if additional_mappings:
            mappings.update(additional_mappings)

        attributes = AttributeExtractor.extract_safely(kwargs, mappings)

        # Determine request type
        if "messages" in kwargs:
            attributes[SpanAttributes.LLM_REQUEST_TYPE] = LLMRequestTypeValues.CHAT.value
        elif "prompt" in kwargs:
            attributes[SpanAttributes.LLM_REQUEST_TYPE] = LLMRequestTypeValues.COMPLETION.value
        elif "input" in kwargs and "embedding" in str(kwargs.get("model", "")):
            attributes[SpanAttributes.LLM_REQUEST_TYPE] = LLMRequestTypeValues.EMBEDDING.value

        return attributes

    @classmethod
    def extract_response_attributes(
        cls, response: Any, additional_mappings: Optional[AttributeMap] = None
    ) -> AttributeMap:
        """Extract standard LLM response attributes.

        Args:
            response: The LLM response object
            additional_mappings: Provider-specific mappings to include

        Returns:
            Extracted attributes
        """
        # Merge standard and additional mappings
        mappings = cls.RESPONSE_ATTRIBUTES.copy()
        if additional_mappings:
            mappings.update(additional_mappings)

        attributes = AttributeExtractor.extract_safely(response, mappings)

        # Extract usage if available
        if hasattr(response, "usage") and response.usage:
            usage_attrs = AttributeExtractor.extract_safely(response.usage, cls.USAGE_ATTRIBUTES)
            attributes.update(usage_attrs)

        return attributes

    @classmethod
    def extract_token_usage(cls, usage_data: Any, additional_mappings: Optional[AttributeMap] = None) -> AttributeMap:
        """Extract token usage attributes.

        Args:
            usage_data: Usage data object
            additional_mappings: Provider-specific usage mappings

        Returns:
            Extracted usage attributes
        """
        mappings = cls.USAGE_ATTRIBUTES.copy()
        if additional_mappings:
            mappings.update(additional_mappings)

        return AttributeExtractor.extract_safely(usage_data, mappings)


class MessageAttributeHandler:
    """Common attribute handling for message content."""

    @staticmethod
    def extract_messages(messages: List[Dict[str, Any]], attribute_type: str = "prompt") -> AttributeMap:
        """Extract attributes from message lists.

        Args:
            messages: List of message dictionaries
            attribute_type: Type of attributes ("prompt" or "completion")

        Returns:
            Extracted message attributes
        """
        attributes = {}

        for i, message in enumerate(messages):
            if attribute_type == "prompt":
                base_attrs = {
                    MessageAttributes.PROMPT_ROLE.format(i=i): "role",
                    MessageAttributes.PROMPT_CONTENT.format(i=i): "content",
                }
            else:
                base_attrs = {
                    MessageAttributes.COMPLETION_ROLE.format(i=i): "role",
                    MessageAttributes.COMPLETION_CONTENT.format(i=i): "content",
                }

            msg_attrs = AttributeExtractor.extract_safely(message, base_attrs)
            attributes.update(msg_attrs)

            # Handle tool calls if present
            if "tool_calls" in message and message["tool_calls"]:
                tool_attrs = MessageAttributeHandler._extract_tool_calls(message["tool_calls"], i, attribute_type)
                attributes.update(tool_attrs)

        return attributes

    @staticmethod
    def _extract_tool_calls(tool_calls: List[Dict[str, Any]], message_index: int, attribute_type: str) -> AttributeMap:
        """Extract attributes from tool calls.

        Args:
            tool_calls: List of tool call dictionaries
            message_index: Index of the parent message
            attribute_type: Type of attributes

        Returns:
            Extracted tool call attributes
        """
        attributes = {}

        for j, tool_call in enumerate(tool_calls):
            if attribute_type == "prompt":
                tool_attrs_map = {
                    MessageAttributes.TOOL_CALL_ID.format(i=message_index): "id",
                    MessageAttributes.TOOL_CALL_TYPE.format(i=message_index): "type",
                    MessageAttributes.TOOL_CALL_NAME.format(i=message_index): "name",
                    MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=message_index): "arguments",
                }
            else:
                tool_attrs_map = {
                    MessageAttributes.COMPLETION_TOOL_CALL_ID.format(i=message_index, j=j): "id",
                    MessageAttributes.COMPLETION_TOOL_CALL_TYPE.format(i=message_index, j=j): "type",
                    MessageAttributes.COMPLETION_TOOL_CALL_NAME.format(i=message_index, j=j): "name",
                    MessageAttributes.COMPLETION_TOOL_CALL_ARGUMENTS.format(i=message_index, j=j): "arguments",
                }

            tool_attrs = AttributeExtractor.extract_safely(tool_call, tool_attrs_map)

            # Handle function details if present
            if "function" in tool_call:
                func_attrs = AttributeExtractor.extract_safely(
                    tool_call["function"], {"name": "name", "arguments": "arguments"}
                )
                # Update the attributes with function details
                for key, value in func_attrs.items():
                    if key == "name" and attribute_type == "completion":
                        attributes[MessageAttributes.COMPLETION_TOOL_CALL_NAME.format(i=message_index, j=j)] = value
                    elif key == "arguments" and attribute_type == "completion":
                        attributes[
                            MessageAttributes.COMPLETION_TOOL_CALL_ARGUMENTS.format(i=message_index, j=j)
                        ] = value

            attributes.update(tool_attrs)

        return attributes


class StreamingAttributeHandler:
    """Common attribute handling for streaming responses."""

    @staticmethod
    def create_streaming_handler(span_attribute_prefix: str = "stream") -> Callable:
        """Create a handler for streaming attributes.

        Args:
            span_attribute_prefix: Prefix for streaming attributes

        Returns:
            Handler function
        """

        def handler(chunk: Any, chunk_index: int, accumulated_content: str = "") -> AttributeMap:
            """Handle attributes from a streaming chunk.

            Args:
                chunk: The streaming chunk
                chunk_index: Index of this chunk
                accumulated_content: Content accumulated so far

            Returns:
                Attributes to set on the span
            """
            attributes = {}

            # Track chunk metadata
            attributes[f"{span_attribute_prefix}.chunk_index"] = chunk_index

            # Extract content from chunk
            if hasattr(chunk, "choices") and chunk.choices:
                choice = chunk.choices[0]
                if hasattr(choice, "delta"):
                    delta = choice.delta
                    if hasattr(delta, "content") and delta.content:
                        attributes[f"{span_attribute_prefix}.chunk_content"] = delta.content
                    if hasattr(delta, "tool_calls") and delta.tool_calls:
                        attributes[f"{span_attribute_prefix}.has_tool_calls"] = True

            # Track accumulated content length
            if accumulated_content:
                attributes[f"{span_attribute_prefix}.accumulated_length"] = len(accumulated_content)

            return attributes

        return handler


def create_composite_handler(
    *handlers: Callable[[Optional[Tuple], Optional[Dict], Optional[Any]], AttributeMap],
) -> Callable[[Optional[Tuple], Optional[Dict], Optional[Any]], AttributeMap]:
    """Create a composite handler that combines multiple attribute handlers.

    Args:
        *handlers: Handler functions to combine

    Returns:
        Combined handler function
    """

    def composite_handler(
        args: Optional[Tuple] = None, kwargs: Optional[Dict] = None, return_value: Optional[Any] = None
    ) -> AttributeMap:
        """Execute all handlers and merge their results.

        Args:
            args: Method arguments
            kwargs: Method keyword arguments
            return_value: Method return value

        Returns:
            Merged attributes from all handlers
        """
        all_attributes = {}

        for handler in handlers:
            try:
                attributes = handler(args=args, kwargs=kwargs, return_value=return_value)
                if attributes:
                    all_attributes.update(attributes)
            except Exception as e:
                logger.debug(f"Error in composite handler: {e}")

        return all_attributes

    return composite_handler


def with_attribute_filter(
    handler: Callable, include_patterns: Optional[List[str]] = None, exclude_patterns: Optional[List[str]] = None
) -> Callable:
    """Wrap a handler to filter attributes based on patterns.

    Args:
        handler: The handler to wrap
        include_patterns: Patterns to include (if None, include all)
        exclude_patterns: Patterns to exclude

    Returns:
        Wrapped handler
    """

    @wraps(handler)
    def filtered_handler(*args, **kwargs) -> AttributeMap:
        attributes = handler(*args, **kwargs)

        if not attributes:
            return attributes

        # Apply include filter
        if include_patterns:
            filtered = {}
            for key, value in attributes.items():
                if any(pattern in key for pattern in include_patterns):
                    filtered[key] = value
            attributes = filtered

        # Apply exclude filter
        if exclude_patterns:
            attributes = {k: v for k, v in attributes.items() if not any(pattern in k for pattern in exclude_patterns)}

        return attributes

    return filtered_handler
