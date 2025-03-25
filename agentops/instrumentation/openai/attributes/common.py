from typing import Any
from agentops.semconv import (
    InstrumentationAttributes
)
from agentops.instrumentation.openai import LIBRARY_NAME, LIBRARY_VERSION
from agentops.instrumentation.common.attributes import AttributeMap
from agentops.instrumentation.common.attributes import get_common_attributes
from agentops.instrumentation.openai.attributes.response import get_response_response_attributes


# Attribute mapping for ResponseSpanData
RESPONSE_SPAN_ATTRIBUTES: AttributeMap = {
}


def get_common_instrumentation_attributes() -> AttributeMap:
    """Get common instrumentation attributes for the OpenAI Agents instrumentation.
    
    This combines the generic AgentOps attributes with OpenAI Agents specific library attributes.
    
    Returns:
        Dictionary of common instrumentation attributes
    """
    attributes = get_common_attributes()
    attributes.update({
        InstrumentationAttributes.LIBRARY_NAME: LIBRARY_NAME,
        InstrumentationAttributes.LIBRARY_VERSION: LIBRARY_VERSION,
    })
    return attributes


def get_response_span_attributes(span_data: Any) -> AttributeMap:
    """Extract attributes from a ResponseSpanData object.
    
    Responses are requests made to the `openai.responses` endpoint.
    
    Args:
        span_data: The ResponseSpanData object
        
    Returns:
        Dictionary of attributes for response span
    """
    attributes = get_response_response_attributes(span_data)
    attributes.update(get_common_attributes())
    
    return attributes

