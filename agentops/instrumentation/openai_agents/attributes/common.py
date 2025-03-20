"""Common utilities and constants for attribute processing.

This module contains shared constants, attribute mappings, and utility functions for processing
trace and span attributes in OpenAI Agents instrumentation. It provides the core functionality
for extracting and formatting attributes according to OpenTelemetry semantic conventions.
"""
import importlib.metadata
from typing import TypeVar, Generic
from typing import Any, Dict, List, Union
from opentelemetry.trace import SpanKind
from agentops.logging import logger
from agentops.helpers import get_agentops_version, safe_serialize
from agentops.semconv import (
    CoreAttributes,
    AgentAttributes,
    WorkflowAttributes,
    SpanAttributes,
    MessageAttributes,
    InstrumentationAttributes
)
from agentops.instrumentation.openai_agents import LIBRARY_NAME, LIBRARY_VERSION
from agentops.instrumentation.openai_agents.attributes.completion import get_generation_output_attributes
from agentops.instrumentation.openai_agents.attributes.model import extract_model_config

# target_attribute_key: source_attribute
AttributeMap = Dict[str, Any]


# Common attribute mapping for all span types
COMMON_ATTRIBUTES: AttributeMap = {
    CoreAttributes.TRACE_ID: "trace_id",
    CoreAttributes.SPAN_ID: "span_id",
    CoreAttributes.PARENT_ID: "parent_id",
}


# Attribute mapping for AgentSpanData
AGENT_SPAN_ATTRIBUTES: AttributeMap = {
    AgentAttributes.AGENT_NAME: "name",
    WorkflowAttributes.WORKFLOW_INPUT: "input",
    WorkflowAttributes.FINAL_OUTPUT: "output",
    AgentAttributes.AGENT_TOOLS: "tools",
    AgentAttributes.HANDOFFS: "handoffs",
}


# Attribute mapping for FunctionSpanData
FUNCTION_SPAN_ATTRIBUTES: AttributeMap = {
    AgentAttributes.AGENT_NAME: "name",
    WorkflowAttributes.WORKFLOW_INPUT: "input",
    WorkflowAttributes.FINAL_OUTPUT: "output",
    AgentAttributes.FROM_AGENT: "from_agent",
}


# Attribute mapping for GenerationSpanData
GENERATION_SPAN_ATTRIBUTES: AttributeMap = {
    SpanAttributes.LLM_REQUEST_MODEL: "model",
    SpanAttributes.LLM_RESPONSE_MODEL: "model",
    SpanAttributes.LLM_PROMPTS: "input",
    # TODO tools - we don't have a semantic convention for this yet
}


# Attribute mapping for HandoffSpanData
HANDOFF_SPAN_ATTRIBUTES: AttributeMap = {
    AgentAttributes.FROM_AGENT: "from_agent",
    AgentAttributes.TO_AGENT: "to_agent",
}


# Attribute mapping for ResponseSpanData
RESPONSE_SPAN_ATTRIBUTES: AttributeMap = {
    WorkflowAttributes.WORKFLOW_INPUT: "input",
    WorkflowAttributes.FINAL_OUTPUT: "response",
}


def _extract_attributes_from_mapping(span_data: Any, attribute_mapping: AttributeMap) -> AttributeMap:
    """Helper function to extract attributes based on a mapping.
    
    Args:
        span_data: The span data object to extract attributes from
        attribute_mapping: Dictionary mapping target attributes to source attributes
        
    Returns:
        Dictionary of extracted attributes
    """
    attributes = {}
    for target_attr, source_attr in attribute_mapping.items():
        if hasattr(span_data, source_attr):
            value = getattr(span_data, source_attr)
            
            # Skip if value is None or empty
            if value is None or (isinstance(value, (list, dict, str)) and not value):
                continue
            
            # Join lists to comma-separated strings
            if source_attr == "tools" or source_attr == "handoffs":
                if isinstance(value, list):
                    value = ",".join(value)
                else:
                    value = str(value)
            # Serialize complex objects
            elif isinstance(value, (dict, list, object)) and not isinstance(value, (str, int, float, bool)):
                value = safe_serialize(value)
            
            attributes[target_attr] = value
    
    return attributes


def get_span_kind(span: Any) -> SpanKind:
    """Determine the appropriate span kind based on span type."""
    span_data = span.span_data
    span_type = span_data.__class__.__name__
    
    if span_type == "AgentSpanData":
        return SpanKind.CONSUMER
    elif span_type in ["FunctionSpanData", "GenerationSpanData", "ResponseSpanData"]:
        return SpanKind.CLIENT
    else:
        return SpanKind.INTERNAL


def get_common_instrumentation_attributes() -> AttributeMap:
    """Get common instrumentation attributes used across traces and spans.
    
    Returns:
        Dictionary of common instrumentation attributes
    """
    return {
        InstrumentationAttributes.NAME: "agentops",
        InstrumentationAttributes.VERSION: get_agentops_version(),
        InstrumentationAttributes.LIBRARY_NAME: LIBRARY_NAME,
        InstrumentationAttributes.LIBRARY_VERSION: LIBRARY_VERSION,
    }


def get_base_trace_attributes(trace: Any) -> AttributeMap:
    """Create the base attributes dictionary for an OpenTelemetry trace.
    
    Args:
        trace: The trace object to extract attributes from
        
    Returns:
        Dictionary containing base trace attributes
    """
    if not hasattr(trace, 'trace_id'):
        logger.warning("Cannot create trace attributes: missing trace_id")
        return {}
    
    attributes = {
        WorkflowAttributes.WORKFLOW_NAME: trace.name,
        CoreAttributes.TRACE_ID: trace.trace_id,
        WorkflowAttributes.WORKFLOW_STEP_TYPE: "trace",
        **get_common_instrumentation_attributes()
    }
    
    return attributes


def get_base_span_attributes(span: Any) -> AttributeMap:
    """Create the base attributes dictionary for an OpenTelemetry span.
    
    Args:
        span: The span object to extract attributes from
        
    Returns:
        Dictionary containing base span attributes
    """
    span_id = getattr(span, 'span_id', 'unknown')
    trace_id = getattr(span, 'trace_id', 'unknown')
    parent_id = getattr(span, 'parent_id', None)
    
    attributes = {
        CoreAttributes.TRACE_ID: trace_id,
        CoreAttributes.SPAN_ID: span_id,
        **get_common_instrumentation_attributes(),
    }
    
    if parent_id:
        attributes[CoreAttributes.PARENT_ID] = parent_id
        
    return attributes


get_agent_span_attributes = lambda span_data: \
    _extract_attributes_from_mapping(span_data, AGENT_SPAN_ATTRIBUTES)

get_function_span_attributes = lambda span_data: \
    _extract_attributes_from_mapping(span_data, FUNCTION_SPAN_ATTRIBUTES)

get_response_span_attributes = lambda span_data: \
    _extract_attributes_from_mapping(span_data, RESPONSE_SPAN_ATTRIBUTES)

get_handoff_span_attributes = lambda span_data: \
    _extract_attributes_from_mapping(span_data, HANDOFF_SPAN_ATTRIBUTES)


"""
Response(
    id='resp_67dc7bcf54808192a4595217d26bc8790bfa203c23b48a1d', 
    created_at=1742502863.0, error=None, incomplete_details=None, 
    instructions='You are a helpful assistant. Your task is to answer questions about programming concepts.', 
    metadata={}, model='gpt-4o-2024-08-06', object='response', 
    output=[ResponseOutputMessage(
        id='msg_67dc7bcfeecc8192846c9ce302a646c80bfa203c23b48a1d', 
        content=[ResponseOutputText(
            annotations=[], 
            text="Recursion in programming is a technique where a function calls itself in order to solve a problem. This method is often used to break down complex problems into simpler, more manageable subproblems. Here's a basic rundown of how recursion works:\n\n### Key Concepts\n\n1. **Base Case**: Every recursive function needs a base case to terminate. This prevents the function from calling itself indefinitely. The base case is a condition that, when true, stops further recursive calls.\n\n2. **Recursive Case**: This is where the function calls itself with a different set of parameters, moving towards the base case.\n\n### How It Works:\n\n- **Define the problem in terms of itself**: Break the problem into smaller instances of the same problem.\n- **Base Case**: Identify a simple instance of the problem that can be solved directly.\n- **Recursive Step**: Define a rule that relates the problem to simpler versions of itself.\n\n### Advantages\n\n- **Simplicity**: Recursion can simplify code, making it more readable and easier to understand.\n- **Problem Solving**: Suitable for problems that are naturally hierarchical, like tree traversals, fractals, or problems that can be divided into similar subproblems.\n\n### Disadvantages\n\n- **Performance**: Recursive solutions can be memory-intensive and slower because each function call adds a new layer to the call stack.\n- **Stack Overflow**: Too many recursive calls can lead to a stack overflow error if the base case is not correctly defined or reached.\n\n### Example: Factorial\n\nA classic example of a recursive function is the factorial calculation:\n\n```python\ndef factorial(n):\n    if n == 0:  # Base case\n        return 1\n    else:\n        return n * factorial(n - 1)  # Recursive case\n```\n\n### Considerations\n\n- Always ensure there is a base case that will eventually be reached.\n- Be mindful of the computational and memory overhead.\n- Sometimes, iterative solutions may be more efficient than recursive ones.\n\nRecursion is a powerful tool, but it needs to be used judiciously to balance clarity and performance.", 
            type='output_text')], 
        role='assistant', 
        status='completed', 
        type='message')], 
    parallel_tool_calls=True,
    temperature=1.0, 
    tool_choice='auto', 
    tools=[], 
    top_p=1.0, 
    max_output_tokens=None, 
    previous_response_id=None, 
    reasoning=Reasoning(effort=None, generate_summary=None), 
    status='completed', 
    text=ResponseTextConfig(format=ResponseFormatText(type='text')), 
    truncation='disabled', 
    usage=ResponseUsage(input_tokens=52, output_tokens=429, output_tokens_details=OutputTokensDetails(reasoning_tokens=0),
    total_tokens=481, 
    input_tokens_details={'cached_tokens': 0}), 
    user=None, store=True)
"""

def get_generation_span_attributes(span_data: Any) -> AttributeMap:
    """Extract attributes from a GenerationSpanData object.
    
    Args:
        span_data: The GenerationSpanData object
        
    Returns:
        Dictionary of attributes for generation span
    """
    attributes = _extract_attributes_from_mapping(span_data, GENERATION_SPAN_ATTRIBUTES)
    
    # Process output for GenerationSpanData if available
    if hasattr(span_data, 'output') and span_data.output:
        # Get attributes with the dedicated method that handles all formats
        generation_attributes = get_generation_output_attributes(span_data.output)
        attributes.update(generation_attributes)
        
        # Add model config attributes if present
        if hasattr(span_data, 'model_config'):
            model_config_attributes = extract_model_config(span_data.model_config)
            attributes.update(model_config_attributes)
    
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
    else:
        logger.debug(f"[agentops.instrumentation.openai_agents.attributes] Unknown span type: {span_type}")
        attributes = {}
    
    return attributes


