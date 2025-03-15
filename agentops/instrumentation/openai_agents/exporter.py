"""
```markdown
# OpenTelemetry Semantic Conventions for Generative AI Systems

## General GenAI Attributes
|--------------------------------------------|---------|
| `gen_ai.agent.description`                 | string  |
| `gen_ai.agent.id`                          | string  |
| `gen_ai.agent.name`                        | string  |
| `gen_ai.operation.name`                    | string  |
| `gen_ai.output.type`                       | string  |
| `gen_ai.request.choice.count`              | int     |
| `gen_ai.request.encoding_formats`          | string[]|
| `gen_ai.request.frequency_penalty`         | double  |
| `gen_ai.request.max_tokens`                | int     |
| `gen_ai.request.model`                     | string  |
| `gen_ai.request.presence_penalty`          | double  |
| `gen_ai.request.seed`                      | int     |
| `gen_ai.request.stop_sequences`            | string[]|
| `gen_ai.request.temperature`               | double  |
| `gen_ai.request.top_k`                     | double  |
| `gen_ai.request.top_p`                     | double  |
| `gen_ai.response.finish_reasons`           | string[]|
| `gen_ai.response.id`                       | string  |
| `gen_ai.response.model`                    | string  |
| `gen_ai.system`                            | string  |
| `gen_ai.token.type`                        | string  |
| `gen_ai.tool.call.id`                      | string  |
| `gen_ai.tool.name`                         | string  |
| `gen_ai.tool.type`                         | string  |
| `gen_ai.usage.input_tokens`                | int     |
| `gen_ai.usage.output_tokens`               | int     |
|------------------------------------------------------|
|  OpenAI-Specific Attributes                          |
|---------------------------------------------|--------|
| `gen_ai.openai.request.service_tier`        | string |
| `gen_ai.openai.response.service_tier`       | string |
| `gen_ai.openai.response.system_fingerprint` | string |

## GenAI Event Attributes

### Event: `gen_ai.system.message`

| Key              | Type   |
|------------------|--------|
| `gen_ai.system`  | string |

**Body Fields:**

| Key              | Type   |
|------------------|--------|
| `content`        | string |
| `role`           | string |

### Event: `gen_ai.user.message`

| Key              | Type   |
|------------------|--------|
| `gen_ai.system`  | string |
```
"""
import importlib.metadata
import json
from typing import Any, Dict, List, Optional, Union

from opentelemetry.trace import get_tracer, SpanKind, Status, StatusCode
from agentops.semconv import (
    CoreAttributes, 
    WorkflowAttributes,
    InstrumentationAttributes,
    AgentAttributes,
    SpanAttributes,
    MessageAttributes
)
from agentops.helpers.serialization import safe_serialize, model_to_dict
from agentops.instrumentation.openai import process_token_usage, process_token_details
from agentops.logging import logger


LIBRARY_NAME = "agents-sdk"

_library_version: Optional[str] = None

def get_version():
    """Get the version of the agents SDK, or 'unknown' if not found"""
    global _library_version
    try:
        _library_version = importlib.metadata.version("agents")
        return _library_version
    except importlib.metadata.PackageNotFoundError:
        logger.debug("`agents` package not found; unable to determine installed version.")
        return "unknown"


# Define standard model configuration mapping (target → source)
MODEL_CONFIG_MAPPING = {
    # Target semantic convention → source field
    SpanAttributes.LLM_REQUEST_TEMPERATURE: "temperature",
    SpanAttributes.LLM_REQUEST_TOP_P: "top_p",
    SpanAttributes.LLM_REQUEST_FREQUENCY_PENALTY: "frequency_penalty",
    SpanAttributes.LLM_REQUEST_PRESENCE_PENALTY: "presence_penalty",
    SpanAttributes.LLM_REQUEST_MAX_TOKENS: "max_tokens",
}

# Additional token usage mapping to handle different naming conventions (target → source)
TOKEN_USAGE_EXTENDED_MAPPING = {
    # Target semantic convention → source field
    SpanAttributes.LLM_USAGE_PROMPT_TOKENS: "input_tokens",
    SpanAttributes.LLM_USAGE_COMPLETION_TOKENS: "output_tokens",
}

class AgentsDetailedExporter:
    """
    A detailed exporter for Agents SDK traces and spans that forwards them to AgentOps.
    """

    def __init__(self, tracer_provider=None):
        self.tracer_provider = tracer_provider
        
    def _process_model_config(self, model_config: Dict[str, Any], attributes: Dict[str, Any]) -> None:
        """
        Process model configuration parameters and add them to the attributes dictionary.
        Works with both dict and object configurations.
        
        Args:
            model_config: Model configuration dictionary or object
            attributes: Attributes dictionary to update
        """
        # Apply the mapping for all model configuration parameters (target → source)
        for target_attr, source_attr in MODEL_CONFIG_MAPPING.items():
            # Try to access as object attribute
            if hasattr(model_config, source_attr) and getattr(model_config, source_attr) is not None:
                attributes[target_attr] = getattr(model_config, source_attr)
            # Try to access as dictionary key
            elif isinstance(model_config, dict) and source_attr in model_config:
                attributes[target_attr] = model_config[source_attr]
                
    def _process_extended_token_usage(self, usage: Dict[str, Any], attributes: Dict[str, Any]) -> None:
        """
        Process token usage statistics beyond what the standard process_token_usage handles.
        Handles alternate naming conventions (input_tokens/output_tokens).
        
        Args:
            usage: Token usage dictionary
            attributes: Attributes dictionary to update
        """
        # First use the standard token usage processor
        process_token_usage(usage, attributes)
        
        # Then apply extended mappings for tokens if not already set by the standard processor (target → source)
        for target_attr, source_attr in TOKEN_USAGE_EXTENDED_MAPPING.items():
            if source_attr in usage and target_attr not in attributes:
                attributes[target_attr] = usage[source_attr]
                
    def _process_response_metadata(self, response: Dict[str, Any], attributes: Dict[str, Any]) -> None:
        """
        Process common response metadata (model, id, system_fingerprint).
        
        Args:
            response: Response dictionary
            attributes: Attributes dictionary to update
        """
        # Define field mappings - target attribute → source field
        field_mapping = {
            # Target semantic convention → source field
            SpanAttributes.LLM_RESPONSE_MODEL: "model",
            SpanAttributes.LLM_RESPONSE_ID: "id",
            SpanAttributes.LLM_OPENAI_RESPONSE_SYSTEM_FINGERPRINT: "system_fingerprint",
        }
        
        # Apply the mapping for all response metadata fields
        for target_attr, source_key in field_mapping.items():
            if source_key in response:
                attributes[target_attr] = response[source_key]
            
    def _process_chat_completions(self, response: Dict[str, Any], attributes: Dict[str, Any]) -> None:
        """
        Process completions from Chat Completion API format.
        
        Args:
            response: Response dictionary containing chat completions
            attributes: Attributes dictionary to update
        """
        if "choices" not in response:
            return
            
        for i, choice in enumerate(response["choices"]):
            prefix = f"{SpanAttributes.LLM_COMPLETIONS}.{i}"
            
            # Add finish reason
            if "finish_reason" in choice:
                attributes[MessageAttributes.COMPLETION_FINISH_REASON.format(i=i)] = choice["finish_reason"]
            
            # Extract message content
            message = choice.get("message", {})
            
            # Include role (even if None/empty)
            if "role" in message:
                attributes[MessageAttributes.COMPLETION_ROLE.format(i=i)] = message["role"]
                
            # Include content (even if None/empty)
            if "content" in message:
                attributes[MessageAttributes.COMPLETION_CONTENT.format(i=i)] = message["content"]
                
            # Handle tool calls
            if "tool_calls" in message:
                tool_calls = message["tool_calls"]
                for j, tool_call in enumerate(tool_calls):
                    if "function" in tool_call:
                        function = tool_call["function"]
                        attributes[MessageAttributes.TOOL_CALL_ID.format(i=i, j=j)] = tool_call.get("id")
                        attributes[MessageAttributes.TOOL_CALL_NAME.format(i=i, j=j)] = function.get("name")
                        attributes[MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=i, j=j)] = function.get("arguments")
                
            # Handle function calls (legacy)
            if "function_call" in message:
                function_call = message["function_call"]
                attributes[MessageAttributes.FUNCTION_CALL_NAME.format(i=i)] = function_call.get("name")
                attributes[MessageAttributes.FUNCTION_CALL_ARGUMENTS.format(i=i)] = function_call.get("arguments")

    def _process_response_api(self, response: Dict[str, Any], attributes: Dict[str, Any]) -> None:
        """
        Process completions from Response API format.
        
        Args:
            response: Response dictionary containing outputs in Response API format
            attributes: Attributes dictionary to update
        """
        # It's pretty funny that the whole point of the Responses API was to get 
        # us past completions[0], and here we are committing to it for the foreseeable future. 
        if "output" not in response:
            return
            
        for i, item in enumerate(response["output"]):
            prefix = f"{SpanAttributes.LLM_COMPLETIONS}.{i}"
            
            # Include role (even if None/empty)
            if "role" in item:
                attributes[MessageAttributes.COMPLETION_ROLE.format(i=i)] = item["role"]
            
            # Process content (handle both simple and complex content formats)
            if "content" in item:
                content_items = item["content"]
                
                if isinstance(content_items, list):
                    # Combine text from all text items
                    texts = []
                    for content_item in content_items:
                        if content_item.get("type") == "output_text" and "text" in content_item:
                            texts.append(content_item["text"])
                    
                    # Join texts (even if empty)
                    attributes[MessageAttributes.COMPLETION_CONTENT.format(i=i)] = " ".join(texts)
                else:
                    # Include content (even if None/empty)
                    attributes[MessageAttributes.COMPLETION_CONTENT.format(i=i)] = safe_serialize(content_items)
            
            # Handle function/tool calls in the Response API format
            if item.get("type") == "function_call":
                # Map the function call attributes to tool call attributes for consistency
                attributes[MessageAttributes.TOOL_CALL_ID.format(i=i, j=0)] = item.get("id", "")
                attributes[MessageAttributes.TOOL_CALL_NAME.format(i=i, j=0)] = item.get("name", "")
                attributes[MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=i, j=0)] = item.get("arguments", "{}")
            
            # Handle call_id attribute for backward compatibility
            if "call_id" in item:
                # If there's a call_id but no ID was set, use it
                if not attributes.get(MessageAttributes.TOOL_CALL_ID.format(i=i, j=0), ""):
                    attributes[MessageAttributes.TOOL_CALL_ID.format(i=i, j=0)] = item["call_id"]
    
    def _process_completions(self, response: Dict[str, Any], attributes: Dict[str, Any]) -> None:
        """
        Process completions from different API formats (Chat Completion API and Response API).
        
        Args:
            response: Response dictionary containing completions
            attributes: Attributes dictionary to update
        """
        # First try Chat Completion API format
        if "choices" in response:
            self._process_chat_completions(response, attributes)
        
        # Then try Response API format
        elif "output" in response:
            self._process_response_api(response, attributes)
            
    def _process_agent_span(self, span: Any, span_data: Any, attributes: Dict[str, Any]) -> SpanKind:
        """
        Process Agent span data and update attributes.
        
        Args:
            span: The original span object
            span_data: The span data object
            attributes: Attributes dictionary to update
            
        Returns:
            The appropriate SpanKind for this span
        """
        # Define field mappings - target attribute → source field
        # This allows us to map multiple attribute names to the same source field
        field_mapping = {
            AgentAttributes.AGENT_NAME: "name",
            WorkflowAttributes.WORKFLOW_INPUT: "input",
            WorkflowAttributes.FINAL_OUTPUT: "output",
            AgentAttributes.FROM_AGENT: "from_agent",
            "agent.from": "from_agent",  # Also map to gen_ai attribute
            AgentAttributes.TO_AGENT: "to_agent",
            "agent.to": "to_agent",      # Also map to gen_ai attribute
        }
        
        # Process attributes using the mapping
        for target_attr, source_key in field_mapping.items():
            if hasattr(span_data, source_key):
                value = getattr(span_data, source_key)
                
                # For Agent spans, pass string values directly
                if source_key in ("input", "output") and isinstance(value, str):
                    attributes[target_attr] = value
                # For complex objects, use serialization
                elif source_key in ("input", "output"):
                    attributes[target_attr] = safe_serialize(value)
                # For other fields, pass directly
                else:
                    attributes[target_attr] = value
        
        # Process special collections
        if hasattr(span_data, "tools"):
            tools = getattr(span_data, "tools")
            if isinstance(tools, list) and tools is not None:
                attributes[AgentAttributes.AGENT_TOOLS] = ",".join(tools)
            else:
                logger.debug(f"Got Agent tools in an unexpected format: {type(tools)}")
        
        # Always return CONSUMER for Agent spans
        return SpanKind.CONSUMER
        
    def _process_function_span(self, span: Any, span_data: Any, attributes: Dict[str, Any]) -> SpanKind:
        """
        Process Function span data and update attributes.
        
        Args:
            span: The original span object
            span_data: The span data object
            attributes: Attributes dictionary to update
            
        Returns:
            The appropriate SpanKind for this span
        """
        # Define field mappings - target attribute → source field
        field_mapping = {
            AgentAttributes.AGENT_NAME: "name",
            SpanAttributes.LLM_PROMPTS: "input",
            "gen_ai.prompt": "input",                  # For OTel spec
            SpanAttributes.LLM_COMPLETIONS: "output",
            "gen_ai.completion": "output",             # For OTel spec
            AgentAttributes.FROM_AGENT: "from_agent",
        }
        
        # Process attributes using the mapping
        for target_attr, source_key in field_mapping.items():
            if hasattr(span_data, source_key):
                value = getattr(span_data, source_key)
                
                # Handle string values directly
                if source_key in ["input", "output"] and isinstance(value, str):
                    attributes[target_attr] = value
                # For non-string inputs/outputs, serialize
                elif source_key in ["input", "output"]:
                    attributes[target_attr] = safe_serialize(value)
                # For other fields, pass directly
                else:
                    attributes[target_attr] = value
        
        # Process special collections
        if hasattr(span_data, "tools"):
            tools = getattr(span_data, "tools")
            if isinstance(tools, list) and tools is not None:
                attributes[AgentAttributes.AGENT_TOOLS] = ",".join(tools)
            else:
                logger.debug(f"Got Function tools in an unexpected format: {type(tools)}")
        
        # Always return CLIENT for Function spans
        return SpanKind.CLIENT
        
    def _process_generation_span(self, span: Any, span_data: Any, attributes: Dict[str, Any]) -> SpanKind:
        """
        Process Generation span data and update attributes.
        
        Args:
            span: The original span object
            span_data: The span data object
            attributes: Attributes dictionary to update
            
        Returns:
            The appropriate SpanKind for this span
        """
        # Define field mappings - target attribute → source field
        field_mapping = {
            # Target semantic convention → source field
            SpanAttributes.LLM_REQUEST_MODEL: "model",
        }
        
        # Process common fields using the standard target → source mapping
        for target_attr, source_key in field_mapping.items():
            if hasattr(span_data, source_key):
                attributes[target_attr] = getattr(span_data, source_key)
                
        # Set the system attribute if model was found
        if SpanAttributes.LLM_REQUEST_MODEL in attributes:
            attributes[SpanAttributes.LLM_SYSTEM] = "openai"
        
        # Process model configuration if available
        if hasattr(span_data, "model_config"):
            self._process_model_config(span_data.model_config, attributes)
        
        # Process output if available
        if hasattr(span_data, "output"):
            output = span_data.output
            
            # Convert to dict if possible for proper extraction
            response_dict = model_to_dict(output)
            
            if response_dict:
                # Process common response metadata
                self._process_response_metadata(response_dict, attributes)
                
                # Process token usage if available
                if "usage" in response_dict:
                    self._process_extended_token_usage(response_dict["usage"], attributes)
                
                # Process completions
                self._process_completions(response_dict, attributes)
            else:
                # Fallback for non-dict outputs
                attributes[SpanAttributes.LLM_COMPLETIONS] = safe_serialize(output)
        
        # Process usage if available at span level
        if hasattr(span_data, "usage"):
            self._process_extended_token_usage(span_data.usage, attributes)
            
        # Always return CLIENT for Generation spans
        return SpanKind.CLIENT

    def export(self, items: list[Any]) -> None:
        """Export Agents SDK traces and spans to AgentOps."""
        for item in items:
            # Handle both Trace and Span objects from Agents SDK
            if hasattr(item, "spans"):  # Trace object
                self._export_trace(item)
            else:  # Span object
                self._export_span(item)

    def _export_trace(self, trace: Any) -> None:
        """Export an Agents SDK trace to AgentOps."""
        # Get the agents SDK version
        LIBRARY_VERSION = get_version()
        
        # Get the current tracer
        tracer = get_tracer(LIBRARY_NAME, LIBRARY_VERSION, self.tracer_provider)

        # Create a new span for the trace
        with tracer.start_as_current_span(
            name=f"agents.trace.{trace.name}",
            kind=SpanKind.INTERNAL,
            attributes={
                WorkflowAttributes.WORKFLOW_NAME: trace.name,
                CoreAttributes.TRACE_ID: trace.trace_id,
                InstrumentationAttributes.LIBRARY_NAME: LIBRARY_NAME,
                InstrumentationAttributes.LIBRARY_VERSION: LIBRARY_VERSION,
                WorkflowAttributes.WORKFLOW_STEP_TYPE: "trace",
            },
        ) as span:
            # Add any additional attributes from the trace
            if hasattr(trace, "group_id") and trace.group_id:
                span.set_attribute(CoreAttributes.GROUP_ID, trace.group_id)

    def _export_span(self, span: Any) -> None:
        """Export an Agents SDK span to AgentOps following semantic conventions."""
        # Get the agents SDK version
        LIBRARY_VERSION = get_version()
        
        # Get the current tracer
        tracer = get_tracer(LIBRARY_NAME, LIBRARY_VERSION, self.tracer_provider)

        span_data = span.span_data
        span_type = span_data.__class__.__name__

        # Create base attributes dictionary with standard fields
        attributes = {
            CoreAttributes.TRACE_ID: span.trace_id,
            CoreAttributes.SPAN_ID: span.span_id,
            InstrumentationAttributes.LIBRARY_NAME: LIBRARY_NAME,
            InstrumentationAttributes.LIBRARY_VERSION: LIBRARY_VERSION,
        }

        # Add parent ID if available
        if span.parent_id:
            attributes[CoreAttributes.PARENT_ID] = span.parent_id

        # Add common relationship information - these should be added regardless of span type
        common_fields = {
            # Map each target attribute to its source field
            AgentAttributes.FROM_AGENT: "from_agent",
            "agent.from": "from_agent",  # Also map to gen_ai attribute
            AgentAttributes.TO_AGENT: "to_agent",
            "agent.to": "to_agent",      # Also map to gen_ai attribute
        }
        
        # Process common fields
        for target_attr, source_key in common_fields.items():
            if hasattr(span_data, source_key):
                attributes[target_attr] = getattr(span_data, source_key)
        
        # Process list fields that need to be joined
        list_fields = {
            # Map each target attribute to its source field
            AgentAttributes.AGENT_TOOLS: "tools",
            AgentAttributes.HANDOFFS: "handoffs",
        }
        
        for target_attr, source_key in list_fields.items():
            if hasattr(span_data, source_key):
                value = getattr(span_data, source_key)
                if value is not None:  # Guard against None
                    attributes[target_attr] = ",".join(value)
            
        # Extract the type for naming (without 'SpanData' suffix)
        type_for_name = span_type.replace("SpanData", "").lower()
        span_name = f"agents.{type_for_name}"
        span_kind = SpanKind.INTERNAL  # Default
        
        # Use type-specific processors based on the exact class name
        if span_type == "AgentSpanData":
            span_kind = self._process_agent_span(span, span_data, attributes)
        elif span_type == "FunctionSpanData":
            span_kind = self._process_function_span(span, span_data, attributes)
        elif span_type == "GenerationSpanData":
            span_kind = self._process_generation_span(span, span_data, attributes)
        
        return self._create_span(tracer, span_name, span_kind, attributes, span)
    
    def _create_span(self, tracer, span_name, span_kind, attributes, span):
        """Create an OpenTelemetry span with the provided attributes."""
        # Create the OpenTelemetry span
        with tracer.start_as_current_span(name=span_name, kind=span_kind, attributes=attributes) as otel_span:
            # Add error information if available
            if hasattr(span, "error") and span.error:
                otel_span.set_status(Status(StatusCode.ERROR))
                otel_span.record_exception(
                    exception=Exception(span.error.get("message", "Unknown error")),
                    attributes={"error.data": json.dumps(span.error.get("data", {}))},
                )
