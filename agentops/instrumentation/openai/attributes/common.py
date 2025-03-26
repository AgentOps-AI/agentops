from agentops.logging import logger
from agentops.semconv import (
    InstrumentationAttributes
)
from agentops.instrumentation.openai import LIBRARY_NAME, LIBRARY_VERSION
from agentops.instrumentation.common.attributes import AttributeMap
from agentops.instrumentation.common.attributes import get_common_attributes
from agentops.instrumentation.openai.attributes.response import get_response_response_attributes

try:
    from openai.types.responses import Response
except ImportError as e:
    logger.debug(f"[agentops.instrumentation.openai_agents] Could not import OpenAI Agents SDK types: {e}")



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


def get_response_attributes(response: Response) -> AttributeMap:
    """Extract attributes from a ResponseSpanData object.
    
    Responses are requests made to the `openai.responses` endpoint.
    
    Args:
        response: The `openai` `Response` object
        
    Returns:
        Dictionary of attributes for the span
    """
    # TODO include prompt(s)
    attributes = get_response_response_attributes(response)
    attributes.update(get_common_attributes())
    
    return attributes

