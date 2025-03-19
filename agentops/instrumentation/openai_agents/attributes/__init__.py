"""Attribute processing modules for OpenAI Agents instrumentation.

This package provides specialized getter functions that extract and format
OpenTelemetry-compatible attributes from span data. Each function follows a
consistent pattern:

1. Takes span data (or specific parts of span data) as input
2. Processes the data according to semantic conventions
3. Returns a dictionary of formatted attributes

The modules are organized by functional domain:

- common: Core attribute extraction functions for all span types
- tokens: Token usage extraction and processing
- model: Model information and parameter extraction
- completion: Completion content and tool call processing

Each getter function is focused on a single responsibility and does not
modify any global state. Functions are designed to be composable, allowing 
different attribute types to be combined as needed in the exporter.

The separation of attribute extraction (getters in this module) from 
attribute application (managed by exporter) follows the principle of
separation of concerns.
"""

from agentops.instrumentation.openai_agents.attributes.tokens import (
    process_token_usage,
    extract_nested_usage,
    map_token_type_to_metric_name,
    get_token_metric_attributes
)

from agentops.instrumentation.openai_agents.attributes.common import (
    get_span_attributes,
    get_agent_span_attributes,
    get_function_span_attributes,
    get_generation_span_attributes,
    get_handoff_span_attributes,
    get_response_span_attributes,
    get_span_kind,
    get_base_span_attributes,
    get_base_trace_attributes
)

from agentops.instrumentation.openai_agents.attributes.model import (
    get_model_info,
    extract_model_config,
    get_model_and_params_attributes,
    get_model_attributes
)

from agentops.instrumentation.openai_agents.attributes.completion import (
    get_generation_output_attributes,
    get_chat_completions_attributes,
    get_response_api_attributes,
    get_response_metadata_attributes
)

from agentops.instrumentation.openai_agents.attributes.common import (
    get_common_instrumentation_attributes
)

__all__ = [
    # Tokens
    "process_token_usage",
    "extract_nested_usage",
    "map_token_type_to_metric_name",
    
    # Metrics
    "get_token_metric_attributes",
    
    # Spans
    "get_span_attributes",
    "get_agent_span_attributes",
    "get_function_span_attributes",
    "get_generation_span_attributes",
    "get_handoff_span_attributes",
    "get_response_span_attributes",
    "get_span_kind",
    "get_base_span_attributes",
    "get_base_trace_attributes",
    
    # Model
    "get_model_info",
    "extract_model_config",
    "get_model_and_params_attributes",
    "get_model_attributes",
    
    # Completion
    "get_generation_output_attributes",
    "get_chat_completions_attributes",
    "get_response_api_attributes",
    "get_response_metadata_attributes",
    
    # Common
    "get_common_instrumentation_attributes"
]