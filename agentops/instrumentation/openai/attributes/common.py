from typing import Optional, Tuple, Dict
from agentops.logging import logger
from agentops.semconv import InstrumentationAttributes
from agentops.instrumentation.openai import LIBRARY_NAME, LIBRARY_VERSION
from agentops.instrumentation.common.attributes import AttributeMap, get_common_attributes
from agentops.instrumentation.openai.attributes.response import (
    get_response_kwarg_attributes,
    get_response_response_attributes,
)

try:
    from openai.types.responses import Response
except ImportError as e:
    logger.debug(f"[agentops.instrumentation.openai] Could not import OpenAI types: {e}")


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


def get_response_attributes(
    args: Optional[Tuple] = None, kwargs: Optional[Dict] = None, return_value: Optional["Response"] = None
) -> AttributeMap:
    """ """
    # We can get an context object before, and after the request is made, so
    # conditionally handle the data we have available.
    attributes = get_common_instrumentation_attributes()

    # Parse the keyword arguments to extract relevant attributes
    # We do not ever get `args` from this method call since it is a keyword-only method
    if kwargs:
        attributes.update(get_response_kwarg_attributes(kwargs))

    # Parse the return value to extract relevant attributes
    if return_value:
        if isinstance(return_value, Response):
            attributes.update(get_response_response_attributes(return_value))
        else:
            logger.debug(f"[agentops.instrumentation.openai] Got an unexpected return type: {type(return_value)}")

    return attributes
