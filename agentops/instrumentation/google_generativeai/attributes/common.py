"""Common attribute extraction for Google Generative AI instrumentation."""

from typing import Dict, Any, Optional

from agentops.logging import logger
from agentops.semconv import InstrumentationAttributes, SpanAttributes
from agentops.instrumentation.common.attributes import AttributeMap, get_common_attributes
from agentops.instrumentation.google_generativeai import LIBRARY_NAME, LIBRARY_VERSION

def get_common_instrumentation_attributes() -> AttributeMap:
    """Get common instrumentation attributes for the Google Generative AI instrumentation.
    
    This combines the generic AgentOps attributes with Google Generative AI specific library attributes.
    
    Returns:
        Dictionary of common instrumentation attributes
    """
    attributes = get_common_attributes()
    attributes.update({
        InstrumentationAttributes.LIBRARY_NAME: LIBRARY_NAME,
        InstrumentationAttributes.LIBRARY_VERSION: LIBRARY_VERSION,
    })
    return attributes


def extract_request_attributes(kwargs: Dict[str, Any]) -> AttributeMap:
    """Extract request attributes from the function arguments.
    
    Extracts common request parameters that apply to both content generation
    and chat completions, focusing on model parameters and generation settings.
    
    Args:
        kwargs: Request keyword arguments
        
    Returns:
        Dictionary of extracted request attributes
    """
    attributes = {}
    
    if 'model' in kwargs:
        model = kwargs["model"]
        
        # Handle string model names
        if isinstance(model, str):
            attributes[SpanAttributes.LLM_REQUEST_MODEL] = model
        # Handle model objects with _model_name or name attribute
        elif hasattr(model, '_model_name'):
            attributes[SpanAttributes.LLM_REQUEST_MODEL] = model._model_name
        elif hasattr(model, 'name'):
            attributes[SpanAttributes.LLM_REQUEST_MODEL] = model.name
    
    config = kwargs.get('config')
    
    if config:
        try:
            param_names = [
                'temperature', 'top_p', 'top_k', 'max_output_tokens',
                'stop_sequences', 'candidate_count', 'seed',
                'presence_penalty', 'frequency_penalty', 'system_instruction'
            ]
            
            for param in param_names:
                if hasattr(config, param):
                    value = getattr(config, param)
                    if value is not None and not callable(value):
                        if param == 'temperature':
                            attributes[SpanAttributes.LLM_REQUEST_TEMPERATURE] = value
                        elif param == 'max_output_tokens':
                            attributes[SpanAttributes.LLM_REQUEST_MAX_TOKENS] = value
                        elif param == 'top_p':
                            attributes[SpanAttributes.LLM_REQUEST_TOP_P] = value
                        elif param == 'top_k':
                            attributes[SpanAttributes.LLM_REQUEST_TOP_K] = value
                        elif param == 'seed':
                            attributes[SpanAttributes.LLM_REQUEST_SEED] = value
                        else:
                            attributes[f"llm.request.{param}"] = value
        except Exception as e:
            logger.debug(f"Error extracting config parameters: {e}")
    
    if 'stream' in kwargs:
        attributes[SpanAttributes.LLM_REQUEST_STREAMING] = kwargs['stream']
    
    return attributes