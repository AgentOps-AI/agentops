"""Common attribute extraction for Anthropic instrumentation."""

from typing import Dict, Any

from agentops.semconv import InstrumentationAttributes, SpanAttributes
from agentops.instrumentation.common.attributes import AttributeMap, get_common_attributes
from agentops.instrumentation.anthropic import LIBRARY_NAME, LIBRARY_VERSION


def get_common_instrumentation_attributes() -> AttributeMap:
    """Get common instrumentation attributes for the Anthropic instrumentation.

    This combines the generic AgentOps attributes with Anthropic specific library attributes.

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
    if "model" in kwargs:
        attributes[SpanAttributes.LLM_REQUEST_MODEL] = kwargs["model"]

    # Extract max_tokens
    if "max_tokens" in kwargs:
        attributes[SpanAttributes.LLM_REQUEST_MAX_TOKENS] = kwargs["max_tokens"]

    # Extract temperature
    if "temperature" in kwargs:
        attributes[SpanAttributes.LLM_REQUEST_TEMPERATURE] = kwargs["temperature"]

    # Extract top_p
    if "top_p" in kwargs:
        attributes[SpanAttributes.LLM_REQUEST_TOP_P] = kwargs["top_p"]

    # Extract streaming
    if "stream" in kwargs:
        attributes[SpanAttributes.LLM_REQUEST_STREAMING] = kwargs["stream"]

    return attributes
