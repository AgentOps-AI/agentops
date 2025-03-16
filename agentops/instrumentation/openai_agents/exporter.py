"""OpenAI Agents SDK Instrumentation Exporter for AgentOps

IMPORTANT SERIALIZATION RULES:
1. We do not serialize data structures arbitrarily; everything has a semantic convention.
2. Span attributes should use semantic conventions and avoid complex serialized structures.
3. Keep all string data in its original form - do not parse JSON within strings.
4. If a function has JSON attributes for its arguments, do not parse that JSON - keep as string.
5. If a completion or response body text/content contains JSON, keep it as a string.
6. When a semantic convention requires a value to be added to span attributes:
   - DO NOT apply JSON serialization
   - All attribute values should be strings or simple numeric/boolean values
   - If we encounter JSON or an object in an area that expects a string, raise an exception
7. Function arguments and tool call arguments should remain in their raw string form.

CRITICAL: NEVER MANUALLY SET THE ROOT COMPLETION ATTRIBUTES
- DO NOT set SpanAttributes.LLM_COMPLETIONS or "gen_ai.completion" manually
- Let OpenTelemetry backend derive these values from the detailed attributes
- Setting root completion attributes creates duplication and inconsistency

STRUCTURED ATTRIBUTE HANDLING:
- Always use MessageAttributes semantic conventions for content and tool calls
- For chat completions, use MessageAttributes.COMPLETION_CONTENT.format(i=0) 
- For tool calls, use MessageAttributes.TOOL_CALL_NAME.format(i=0, j=0), etc.
- Never try to combine or aggregate contents into a single attribute
- Each message component should have its own properly formatted attribute
- This ensures proper display in OpenTelemetry backends and dashboards

IMPORTANT FOR TESTING:
- Tests should verify attribute existence using MessageAttributes constants
- Do not check for the presence of SpanAttributes.LLM_COMPLETIONS
- Verify individual content/tool attributes instead of root attributes

WAYS TO USE SEMANTIC CONVENTIONS WHEN REFERENCING SPAN ATTRIBUTES:
1. Always use the constant values from the semantic convention classes rather than hardcoded strings:
   ```python
   # Good
   attributes[SpanAttributes.LLM_PROMPTS] = input_value
   
   # Avoid
   attributes["gen_ai.prompt"] = input_value
   ```

2. For structured attributes like completions, use the format methods from MessageAttributes:
   ```python
   # Good
   attributes[MessageAttributes.COMPLETION_CONTENT.format(i=0)] = content
   
   # Avoid
   attributes["gen_ai.completion.0.content"] = content
   ```

3. Be consistent with naming patterns across different span types:
   - Use `SpanAttributes.LLM_PROMPTS` for input/prompt data
   - Use `MessageAttributes.COMPLETION_CONTENT.format(i=0)` for output/response content
   - Use `WorkflowAttributes.FINAL_OUTPUT` for workflow outputs

4. Keep special attributes at their correct levels:
   - Don't manually set root completion attributes (`SpanAttributes.LLM_COMPLETIONS`) 
   - Set MessageAttributes for each individual message component
   - Let the OpenTelemetry backend derive the root attributes

5. When searching for attributes in spans, use the constants from the semantic convention classes:
   ```python
   # Good
   if SpanAttributes.LLM_PROMPTS in span.attributes:
       # Do something
   
   # Avoid
   if "gen_ai.prompt" in span.attributes:
       # Do something
   ```
"""
import json
from typing import Any, Dict, Optional

from opentelemetry import trace
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
from agentops.instrumentation.openai import process_token_usage
from agentops.logging import logger
from agentops.instrumentation.openai_agents import LIBRARY_NAME, LIBRARY_VERSION


def get_model_info(agent: Any, run_config: Any = None) -> Dict[str, Any]:
    """Extract model information from agent and run_config."""
    result = {"model_name": "unknown"}

    if run_config and hasattr(run_config, "model") and run_config.model:
        if isinstance(run_config.model, str):
            result["model_name"] = run_config.model
        elif hasattr(run_config.model, "model") and run_config.model.model:
            result["model_name"] = run_config.model.model

    if result["model_name"] == "unknown" and hasattr(agent, "model") and agent.model:
        if isinstance(agent.model, str):
            result["model_name"] = agent.model
        elif hasattr(agent.model, "model") and agent.model.model:
            result["model_name"] = agent.model.model

    if result["model_name"] == "unknown":
        try:
            from agents.models.openai_provider import DEFAULT_MODEL
            result["model_name"] = DEFAULT_MODEL
        except ImportError:
            pass

    if hasattr(agent, "model_settings") and agent.model_settings:
        model_settings = agent.model_settings

        for param in ["temperature", "top_p", "frequency_penalty", "presence_penalty"]:
            if hasattr(model_settings, param) and getattr(model_settings, param) is not None:
                result[param] = getattr(model_settings, param)

    if run_config and hasattr(run_config, "model_settings") and run_config.model_settings:
        model_settings = run_config.model_settings

        for param in ["temperature", "top_p", "frequency_penalty", "presence_penalty"]:
            if hasattr(model_settings, param) and getattr(model_settings, param) is not None:
                result[param] = getattr(model_settings, param)

    return result


MODEL_CONFIG_MAPPING = {
    SpanAttributes.LLM_REQUEST_TEMPERATURE: "temperature",
    SpanAttributes.LLM_REQUEST_TOP_P: "top_p",
    SpanAttributes.LLM_REQUEST_FREQUENCY_PENALTY: "frequency_penalty",
    SpanAttributes.LLM_REQUEST_PRESENCE_PENALTY: "presence_penalty",
    SpanAttributes.LLM_REQUEST_MAX_TOKENS: "max_tokens",
}

TOKEN_USAGE_EXTENDED_MAPPING = {
    SpanAttributes.LLM_USAGE_PROMPT_TOKENS: "input_tokens",
    SpanAttributes.LLM_USAGE_COMPLETION_TOKENS: "output_tokens",
}

class OpenAIAgentsExporter:
    """A detailed exporter for Agents SDK traces and spans that forwards them to AgentOps."""

    def __init__(self, tracer_provider=None):
        self.tracer_provider = tracer_provider
        self._current_trace_id = None  # Store the current trace ID for consistency
    
    def export_trace(self, trace: Any) -> None:
        """Export a trace object with enhanced attribute extraction."""
        logger.debug(f"[OpenAIAgentsExporter] Exporting trace: {getattr(trace, 'trace_id', 'unknown')}")
        # Export the trace directly
        result = self._export_trace(trace)
        logger.debug(f"[OpenAIAgentsExporter] Trace export complete: {getattr(trace, 'trace_id', 'unknown')}")
        return result
        
    def export_span(self, span: Any) -> None:
        """Export a span object with enhanced attribute extraction."""
        span_id = getattr(span, 'span_id', 'unknown')
        span_type = getattr(span.span_data, '__class__', object).__name__ if hasattr(span, 'span_data') else 'unknown'
        logger.debug(f"[OpenAIAgentsExporter] Exporting span: {span_id} (type: {span_type})")
        
        # Export the span directly
        result = self._export_span(span)
        logger.debug(f"[OpenAIAgentsExporter] Span export result: {span_id}, success={result is not None}")
        return result
    
    def _export_enhanced_trace(self, trace: Any) -> None:
        """Export enhanced trace information."""
        if not self.tracer_provider or not hasattr(trace, 'trace_id'):
            return
            
        tracer = get_tracer(LIBRARY_NAME, LIBRARY_VERSION, self.tracer_provider)
        
        with tracer.start_as_current_span(
            name=f"agents.enhanced_trace.{getattr(trace, 'name', 'unknown')}",
            kind=SpanKind.INTERNAL,
            attributes={
                WorkflowAttributes.WORKFLOW_NAME: getattr(trace, 'name', 'unknown'),
                CoreAttributes.TRACE_ID: trace.trace_id,
                InstrumentationAttributes.NAME: LIBRARY_NAME,
                InstrumentationAttributes.VERSION: LIBRARY_VERSION,
                WorkflowAttributes.WORKFLOW_STEP_TYPE: "trace",
            },
        ) as span:
            # Add any additional trace attributes
            if hasattr(trace, "group_id") and trace.group_id:
                span.set_attribute(CoreAttributes.GROUP_ID, trace.group_id)
                
            if hasattr(trace, "metadata") and trace.metadata:
                for key, value in trace.metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        span.set_attribute(f"trace.metadata.{key}", value)
    
    def _export_enhanced_span(self, span: Any) -> None:
        """Export enhanced span information."""
        if not self.tracer_provider or not hasattr(span, 'span_data'):
            return
            
        span_data = span.span_data
        span_type = span_data.__class__.__name__
        
        if span_type not in ["AgentSpanData", "FunctionSpanData", "GenerationSpanData", 
                            "HandoffSpanData", "GuardrailSpanData", "CustomSpanData"]:
            return  # Skip unsupported span types
            
        # Process the span based on its type
        self._create_enhanced_span(span, span_type)
    
    def _create_enhanced_span(self, span: Any, span_type: str) -> None:
        """Create an enhanced OpenTelemetry span from an Agents SDK span."""
        tracer = get_tracer(LIBRARY_NAME, LIBRARY_VERSION, self.tracer_provider)
        
        # Default span attributes
        attributes = self._get_common_span_attributes(span)
        
        span_name = f"agents.enhanced_{span_type.replace('SpanData', '').lower()}"
        span_kind = SpanKind.INTERNAL
        
        # Process specific span types
        if span_type == "AgentSpanData":
            span_kind = SpanKind.CONSUMER
            self._process_agent_span_attributes(span.span_data, attributes)
        elif span_type == "FunctionSpanData":
            span_kind = SpanKind.CLIENT
            self._process_function_span_attributes(span.span_data, attributes)
        elif span_type == "GenerationSpanData":
            span_kind = SpanKind.CLIENT
            self._process_generation_span_attributes(span.span_data, attributes)
        elif span_type == "HandoffSpanData":
            self._process_handoff_span_attributes(span.span_data, attributes)
        
        # Create OpenTelemetry span
        with tracer.start_as_current_span(
            name=span_name,
            kind=span_kind,
            attributes=attributes
        ) as otel_span:
            # Record error if present
            if hasattr(span, 'error') and span.error:
                otel_span.set_status(Status(StatusCode.ERROR))
                otel_span.record_exception(Exception(str(span.error)))
                otel_span.set_attribute(CoreAttributes.ERROR_TYPE, "AgentError")
                otel_span.set_attribute(CoreAttributes.ERROR_MESSAGE, str(span.error))
    
    def _get_common_span_attributes(self, span: Any) -> Dict[str, Any]:
        """Get common attributes for any span type."""
        attributes = {
            CoreAttributes.TRACE_ID: getattr(span, 'trace_id', 'unknown'),
            CoreAttributes.SPAN_ID: getattr(span, 'span_id', 'unknown'),
            InstrumentationAttributes.NAME: LIBRARY_NAME,
            InstrumentationAttributes.VERSION: LIBRARY_VERSION,
        }
        
        if hasattr(span, 'parent_id') and span.parent_id:
            attributes[CoreAttributes.PARENT_ID] = span.parent_id
            
        return attributes
    
    def _process_agent_span_attributes(self, span_data: Any, attributes: Dict[str, Any]) -> None:
        """Process agent span specific attributes."""
        if hasattr(span_data, 'name'):
            attributes[AgentAttributes.AGENT_NAME] = span_data.name
        
        if hasattr(span_data, 'input'):
            attributes[WorkflowAttributes.WORKFLOW_INPUT] = safe_serialize(span_data.input)
            
        if hasattr(span_data, 'output'):
            attributes[WorkflowAttributes.FINAL_OUTPUT] = safe_serialize(span_data.output)
            
        if hasattr(span_data, 'tools') and span_data.tools:
            attributes[AgentAttributes.AGENT_TOOLS] = ",".join(span_data.tools)
            
        if hasattr(span_data, 'handoffs') and span_data.handoffs:
            attributes[AgentAttributes.HANDOFFS] = ",".join(span_data.handoffs)
    
    def _process_function_span_attributes(self, span_data: Any, attributes: Dict[str, Any]) -> None:
        """Process function span specific attributes."""
        if hasattr(span_data, 'name'):
            attributes[AgentAttributes.AGENT_NAME] = span_data.name
            
        if hasattr(span_data, 'input'):
            attributes[SpanAttributes.LLM_PROMPTS] = safe_serialize(span_data.input)
            
        if hasattr(span_data, 'output'):
            attributes[SpanAttributes.LLM_COMPLETIONS] = safe_serialize(span_data.output)
            
        if hasattr(span_data, 'from_agent'):
            attributes[AgentAttributes.FROM_AGENT] = span_data.from_agent
    
    def _process_generation_span_attributes(self, span_data: Any, attributes: Dict[str, Any]) -> None:
        """Process generation span specific attributes."""
        if hasattr(span_data, 'model'):
            attributes[SpanAttributes.LLM_REQUEST_MODEL] = span_data.model
            attributes[SpanAttributes.LLM_SYSTEM] = "openai"
            
        if hasattr(span_data, 'input'):
            attributes[SpanAttributes.LLM_PROMPTS] = safe_serialize(span_data.input)
            
        if hasattr(span_data, 'output'):
            attributes[SpanAttributes.LLM_COMPLETIONS] = safe_serialize(span_data.output)
            
        if hasattr(span_data, 'model_config'):
            self._process_model_config(span_data.model_config, attributes)
            
        if hasattr(span_data, 'usage'):
            self._process_usage_attributes(span_data.usage, attributes)
    
    def _process_handoff_span_attributes(self, span_data: Any, attributes: Dict[str, Any]) -> None:
        """Process handoff span specific attributes."""
        if hasattr(span_data, 'from_agent'):
            attributes[AgentAttributes.FROM_AGENT] = span_data.from_agent
            
        if hasattr(span_data, 'to_agent'):
            attributes[AgentAttributes.TO_AGENT] = span_data.to_agent
    
    def _process_model_config(self, model_config: Any, attributes: Dict[str, Any]) -> None:
        """Process model configuration parameters."""
        param_mapping = {
            "temperature": SpanAttributes.LLM_REQUEST_TEMPERATURE,
            "top_p": SpanAttributes.LLM_REQUEST_TOP_P,
            "frequency_penalty": SpanAttributes.LLM_REQUEST_FREQUENCY_PENALTY,
            "presence_penalty": SpanAttributes.LLM_REQUEST_PRESENCE_PENALTY,
            "max_tokens": SpanAttributes.LLM_REQUEST_MAX_TOKENS,
        }
        
        for source_param, target_attr in param_mapping.items():
            # Handle both object and dictionary syntax
            if hasattr(model_config, source_param) and getattr(model_config, source_param) is not None:
                attributes[target_attr] = getattr(model_config, source_param)
            elif isinstance(model_config, dict) and source_param in model_config:
                attributes[target_attr] = model_config[source_param]
    
    def _process_usage_attributes(self, usage: Any, attributes: Dict[str, Any]) -> None:
        """Process token usage information."""
        # Handle both object and dictionary syntax
        if hasattr(usage, "prompt_tokens") or hasattr(usage, "input_tokens"):
            prompt_tokens = getattr(usage, "prompt_tokens", getattr(usage, "input_tokens", 0))
            attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = prompt_tokens
            
        if hasattr(usage, "completion_tokens") or hasattr(usage, "output_tokens"):
            completion_tokens = getattr(usage, "completion_tokens", getattr(usage, "output_tokens", 0))
            attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = completion_tokens
            
        if hasattr(usage, "total_tokens"):
            attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = usage.total_tokens
        
        # Dictionary style access
        if isinstance(usage, dict):
            if "prompt_tokens" in usage or "input_tokens" in usage:
                prompt_tokens = usage.get("prompt_tokens", usage.get("input_tokens", 0))
                attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = prompt_tokens
                
            if "completion_tokens" in usage or "output_tokens" in usage:
                completion_tokens = usage.get("completion_tokens", usage.get("output_tokens", 0))
                attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = completion_tokens
                
            if "total_tokens" in usage:
                attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = usage["total_tokens"]
                
            # Handle extended token details
            if "output_tokens_details" in usage:
                details = usage["output_tokens_details"]
                if isinstance(details, dict) and "reasoning_tokens" in details:
                    attributes[SpanAttributes.LLM_USAGE_REASONING_TOKENS] = details["reasoning_tokens"]
    
    def _set_completion_and_final_output(self, attributes: Dict[str, Any], value: Any, role: str = "assistant") -> None:
        """Set completion content attributes and final output consistently across span types."""
        if isinstance(value, str):
            serialized_value = value
        else:
            serialized_value = safe_serialize(value)
        
        # Set as completion content
        attributes[MessageAttributes.COMPLETION_CONTENT.format(i=0)] = serialized_value
        attributes[MessageAttributes.COMPLETION_ROLE.format(i=0)] = role
        
        # Also set as final output
        attributes[WorkflowAttributes.FINAL_OUTPUT] = serialized_value
        
    def _process_model_config(self, model_config: Dict[str, Any], attributes: Dict[str, Any]) -> None:
        for target_attr, source_attr in MODEL_CONFIG_MAPPING.items():
            if hasattr(model_config, source_attr) and getattr(model_config, source_attr) is not None:
                attributes[target_attr] = getattr(model_config, source_attr)
            elif isinstance(model_config, dict) and source_attr in model_config:
                attributes[target_attr] = model_config[source_attr]
                
    def _process_extended_token_usage(self, usage: Dict[str, Any], attributes: Dict[str, Any]) -> None:
        process_token_usage(usage, attributes)
        
        for target_attr, source_attr in TOKEN_USAGE_EXTENDED_MAPPING.items():
            if source_attr in usage and target_attr not in attributes:
                attributes[target_attr] = usage[source_attr]
                
    def _process_response_metadata(self, response: Dict[str, Any], attributes: Dict[str, Any]) -> None:
        field_mapping = {
            SpanAttributes.LLM_RESPONSE_MODEL: "model",
            SpanAttributes.LLM_RESPONSE_ID: "id",
            SpanAttributes.LLM_OPENAI_RESPONSE_SYSTEM_FINGERPRINT: "system_fingerprint",
        }
        
        for target_attr, source_key in field_mapping.items():
            if source_key in response:
                attributes[target_attr] = response[source_key]
            
    def _process_chat_completions(self, response: Dict[str, Any], attributes: Dict[str, Any]) -> None:
        if "choices" not in response:
            return
            
        for i, choice in enumerate(response["choices"]):
            if "finish_reason" in choice:
                attributes[MessageAttributes.COMPLETION_FINISH_REASON.format(i=i)] = choice["finish_reason"]
            
            message = choice.get("message", {})
            
            if "role" in message:
                attributes[MessageAttributes.COMPLETION_ROLE.format(i=i)] = message["role"]
                
            if "content" in message:
                content = message["content"] if message["content"] is not None else ""
                attributes[MessageAttributes.COMPLETION_CONTENT.format(i=i)] = content
                
            if "tool_calls" in message and message["tool_calls"] is not None:
                tool_calls = message["tool_calls"]
                for j, tool_call in enumerate(tool_calls):
                    if "function" in tool_call:
                        function = tool_call["function"]
                        attributes[MessageAttributes.TOOL_CALL_ID.format(i=i, j=j)] = tool_call.get("id")
                        attributes[MessageAttributes.TOOL_CALL_NAME.format(i=i, j=j)] = function.get("name")
                        attributes[MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=i, j=j)] = function.get("arguments")
                
            if "function_call" in message and message["function_call"] is not None:
                function_call = message["function_call"]
                attributes[MessageAttributes.FUNCTION_CALL_NAME.format(i=i)] = function_call.get("name")
                attributes[MessageAttributes.FUNCTION_CALL_ARGUMENTS.format(i=i)] = function_call.get("arguments")

    def _process_response_api(self, response: Dict[str, Any], attributes: Dict[str, Any]) -> None:
        """Process a response from the OpenAI Response API format (used by Agents SDK)"""
        if "output" not in response:
            return
        
        # Process each output item for detailed attributes
        for i, item in enumerate(response["output"]):
            # Extract role if present
            if "role" in item:
                attributes[MessageAttributes.COMPLETION_ROLE.format(i=i)] = item["role"]
            
            # Extract text content if present
            if "content" in item:
                content_items = item["content"]
                
                if isinstance(content_items, list):
                    # Handle content items list (typically for text responses)
                    for content_item in content_items:
                        if content_item.get("type") == "output_text" and "text" in content_item:
                            # Set the content attribute with the text - keep as raw string
                            attributes[MessageAttributes.COMPLETION_CONTENT.format(i=i)] = content_item["text"]
                
                elif isinstance(content_items, str):
                    # Handle string content - keep as raw string
                    attributes[MessageAttributes.COMPLETION_CONTENT.format(i=i)] = content_items
            
            # Extract function/tool call information
            if item.get("type") == "function_call":
                # Get tool call details - keep as raw strings, don't parse JSON
                item_id = item.get("id", "")
                tool_name = item.get("name", "")
                tool_args = item.get("arguments", "")
                
                # Set tool call attributes using standard semantic conventions
                attributes[MessageAttributes.TOOL_CALL_ID.format(i=i, j=0)] = item_id
                attributes[MessageAttributes.TOOL_CALL_NAME.format(i=i, j=0)] = tool_name
                attributes[MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=i, j=0)] = tool_args
            
            # Ensure call_id is captured if present
            if "call_id" in item and not attributes.get(MessageAttributes.TOOL_CALL_ID.format(i=i, j=0), ""):
                attributes[MessageAttributes.TOOL_CALL_ID.format(i=i, j=0)] = item["call_id"]
    
    def _process_completions(self, response: Dict[str, Any], attributes: Dict[str, Any]) -> None:
        if "choices" in response:
            self._process_chat_completions(response, attributes)
        elif "output" in response:
            self._process_response_api(response, attributes)
            
    def _process_agent_span(self, span: Any, span_data: Any, attributes: Dict[str, Any]) -> SpanKind:
        field_mapping = {
            AgentAttributes.AGENT_NAME: "name",
            WorkflowAttributes.WORKFLOW_INPUT: "input",
            WorkflowAttributes.FINAL_OUTPUT: "output",
            AgentAttributes.FROM_AGENT: "from_agent",
            "agent.from": "from_agent",
            AgentAttributes.TO_AGENT: "to_agent",
            "agent.to": "to_agent",
        }
        
        for target_attr, source_key in field_mapping.items():
            if hasattr(span_data, source_key):
                value = getattr(span_data, source_key)
                
                if source_key in ("input", "output") and isinstance(value, str):
                    attributes[target_attr] = value
                    
                    # If this is the output, also set it as a completion content
                    if source_key == "output":
                        self._set_completion_and_final_output(attributes, value)
                elif source_key in ("input", "output"):
                    serialized_value = safe_serialize(value)
                    attributes[target_attr] = serialized_value
                    
                    # If this is the output, also set it as a completion content
                    if source_key == "output":
                        self._set_completion_and_final_output(attributes, value)
                else:
                    attributes[target_attr] = value
        
        if hasattr(span_data, "tools"):
            tools = getattr(span_data, "tools")
            if isinstance(tools, list) and tools is not None:
                attributes[AgentAttributes.AGENT_TOOLS] = ",".join(tools)
            else:
                logger.debug(f"Got Agent tools in an unexpected format: {type(tools)}")
        
        return SpanKind.CONSUMER
        
    def _process_function_span(self, span: Any, span_data: Any, attributes: Dict[str, Any]) -> SpanKind:
        field_mapping = {
            AgentAttributes.AGENT_NAME: "name",
            SpanAttributes.LLM_PROMPTS: "input",
            "gen_ai.prompt": "input",
            # Note: We don't set LLM_COMPLETIONS directly per serialization rules
            # Instead, use MessageAttributes for structured completion data
            AgentAttributes.FROM_AGENT: "from_agent",
        }
        
        for target_attr, source_key in field_mapping.items():
            if hasattr(span_data, source_key):
                value = getattr(span_data, source_key)
                
                if source_key in ["input", "output"] and isinstance(value, str):
                    attributes[target_attr] = value
                elif source_key in ["input", "output"]:
                    attributes[target_attr] = safe_serialize(value)
                else:
                    attributes[target_attr] = value
        
        # If this function has an output, add it as completion content using MessageAttributes
        if hasattr(span_data, "output"):
            output_value = getattr(span_data, "output")
            self._set_completion_and_final_output(attributes, output_value, role="function")
        
        if hasattr(span_data, "tools"):
            tools = getattr(span_data, "tools")
            if isinstance(tools, list) and tools is not None:
                attributes[AgentAttributes.AGENT_TOOLS] = ",".join(tools)
            else:
                logger.debug(f"Got Function tools in an unexpected format: {type(tools)}")
        
        return SpanKind.CLIENT
        
    def _process_generation_span(self, span: Any, span_data: Any, attributes: Dict[str, Any]) -> SpanKind:
        """Process a generation span from the Agents SDK
        
        This method extracts information from a GenerationSpanData object and
        sets appropriate span attributes for the OpenTelemetry backend.
        
        Args:
            span: The original span object from the SDK
            span_data: The span_data object containing generation details
            attributes: Dictionary to add attributes to
        
        Returns:
            The appropriate span kind (CLIENT)
        """
        # Map basic model information
        field_mapping = {
            SpanAttributes.LLM_REQUEST_MODEL: "model",
        }
        
        for target_attr, source_key in field_mapping.items():
            if hasattr(span_data, source_key):
                attributes[target_attr] = getattr(span_data, source_key)
                
        # Set the system to OpenAI when we have model information
        if SpanAttributes.LLM_REQUEST_MODEL in attributes:
            attributes[SpanAttributes.LLM_SYSTEM] = "openai"
        
        # Process model configuration if present
        if hasattr(span_data, "model_config"):
            self._process_model_config(span_data.model_config, attributes)
        
        # Set input in standardized location
        # Dude, I think what we really want to do here instead of safely serializing 
        # any input that's not a string is to reference the original input content. 
        # We're getting tripped up on serialization because sometimes the input is a 
        # JSON object. On the way out, as we decode the response from the LLM, it 
        # might contain a JSON object. But we don't need to handle those. We should 
        # just keep unparsed JSON as a string. This applies to any attributes (mostly 
        # input and output) but also when you're looking at function call keys or even
        # function call responses. If a function call response is JSON but is not part 
        # of our schema, then we should put a stringified JSON in place. 
        if hasattr(span_data, "input"):
            attributes[SpanAttributes.LLM_PROMPTS] = (
                span_data.input if isinstance(span_data.input, str) 
                else safe_serialize(span_data.input)
            )
        
        # Process output/response data
        if hasattr(span_data, "output"):
            output = span_data.output
            
            # Convert model to dictionary for easier processing
            response_dict = model_to_dict(output)
            
            if response_dict:
                # Extract metadata (model, id, system fingerprint)
                self._process_response_metadata(response_dict, attributes)
                
                # Process token usage metrics
                if "usage" in response_dict:
                    self._process_extended_token_usage(response_dict["usage"], attributes)
                
                # Process response content based on format (chat completion or response API)
                self._process_completions(response_dict, attributes)
                
                # NOTE: We don't set the root completion attribute (gen_ai.completion)
                # The OpenTelemetry backend will derive it from detailed attributes
                # See the note at the top of this file for why we don't do this
        
        # Process any usage data directly on the span
        if hasattr(span_data, "usage"):
            self._process_extended_token_usage(span_data.usage, attributes)
        
        # If we have output but no completion attributes were set during processing,
        # set the output as completion content
        if hasattr(span_data, "output") and "gen_ai.completion.0.content" not in attributes:
            output = span_data.output
            if isinstance(output, str):
                self._set_completion_and_final_output(attributes, output)
            elif hasattr(output, "output") and isinstance(output.output, list) and output.output:
                # Handle API response format
                first_output = output.output[0]
                if hasattr(first_output, "content") and first_output.content:
                    content_value = first_output.content
                    if isinstance(content_value, list) and content_value and hasattr(content_value[0], "text"):
                        self._set_completion_and_final_output(attributes, content_value[0].text)
                    elif isinstance(content_value, str):
                        self._set_completion_and_final_output(attributes, content_value)
            
        return SpanKind.CLIENT

    # def export_trace(self, trace: Any) -> None:
    #     """Export a trace object directly."""
    #     self._export_trace(trace)
        
    # def export_span(self, span: Any) -> None:
    #     """Export a span object directly."""
    #     self._export_span(span)

    def _export_trace(self, trace: Any) -> None:
        """Export a trace object with enhanced attribute extraction."""
        # Get tracer from provider or use direct get_tracer if no provider
        tracer = get_tracer(LIBRARY_NAME, LIBRARY_VERSION, self.tracer_provider)
        
        if not hasattr(trace, 'trace_id'):
            logger.warning("Cannot export trace: missing trace_id")
            return
        
        # Create the trace span directly
        span = tracer.start_span(
            name=f"agents.trace.{trace.name}",
            kind=SpanKind.INTERNAL,
            attributes={
                WorkflowAttributes.WORKFLOW_NAME: trace.name,
                CoreAttributes.TRACE_ID: trace.trace_id,
                InstrumentationAttributes.LIBRARY_NAME: LIBRARY_NAME,
                InstrumentationAttributes.LIBRARY_VERSION: LIBRARY_VERSION,
                WorkflowAttributes.WORKFLOW_STEP_TYPE: "trace",
            },
        )
        
        # Add any additional trace attributes
        if hasattr(trace, "group_id") and trace.group_id:
            span.set_attribute(CoreAttributes.GROUP_ID, trace.group_id)
            
        if hasattr(trace, "metadata") and trace.metadata:
            for key, value in trace.metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    span.set_attribute(f"trace.metadata.{key}", value)
        
        # End the span to ensure it's exported
        span.end()
        
        # Debug log to verify span creation 
        logger.debug(f"Created and ended trace span: agents.trace.{trace.name}")

    def _export_span(self, span: Any) -> None:
        tracer = get_tracer(LIBRARY_NAME, LIBRARY_VERSION, self.tracer_provider)

        span_data = span.span_data
        span_type = span_data.__class__.__name__
        
        # Verify this is a known span type
        if span_type not in ["AgentSpanData", "FunctionSpanData", "GenerationSpanData", 
                            "HandoffSpanData", "GuardrailSpanData", "CustomSpanData", "ResponseSpanData"]:
            span_id = getattr(span, 'span_id', 'unknown')
            logger.debug(f"Unknown span type: {span_type}, span_id={span_id}")
            # Continue anyway...

        attributes = {
            CoreAttributes.TRACE_ID: span.trace_id,
            CoreAttributes.SPAN_ID: span.span_id,
            InstrumentationAttributes.LIBRARY_NAME: LIBRARY_NAME,
            InstrumentationAttributes.LIBRARY_VERSION: LIBRARY_VERSION,
        }

        if span.parent_id:
            attributes[CoreAttributes.PARENT_ID] = span.parent_id

        common_fields = {
            AgentAttributes.FROM_AGENT: "from_agent",
            "agent.from": "from_agent",
            AgentAttributes.TO_AGENT: "to_agent",
            "agent.to": "to_agent",
        }
        
        for target_attr, source_key in common_fields.items():
            if hasattr(span_data, source_key):
                attributes[target_attr] = getattr(span_data, source_key)
        
        list_fields = {
            AgentAttributes.AGENT_TOOLS: "tools",
            AgentAttributes.HANDOFFS: "handoffs",
        }
        
        for target_attr, source_key in list_fields.items():
            if hasattr(span_data, source_key):
                value = getattr(span_data, source_key)
                if value is not None:
                    attributes[target_attr] = ",".join(value)
            
        type_for_name = span_type.replace("SpanData", "").lower()
        span_name = f"agents.{type_for_name}"
        span_kind = SpanKind.INTERNAL
        
        if span_type == "AgentSpanData":
            span_kind = self._process_agent_span(span, span_data, attributes)
        elif span_type == "FunctionSpanData":
            span_kind = self._process_function_span(span, span_data, attributes)
        elif span_type == "GenerationSpanData":
            span_kind = self._process_generation_span(span, span_data, attributes)
        elif span_type == "ResponseSpanData":
            # For ResponseSpanData, process input and response attributes
            if hasattr(span_data, "input"):
                input_value = span_data.input
                input_str = input_value if isinstance(input_value, str) else safe_serialize(input_value)
                attributes[SpanAttributes.LLM_PROMPTS] = input_str
                attributes[WorkflowAttributes.WORKFLOW_INPUT] = input_str
            
            if hasattr(span_data, "response"):
                response = span_data.response
                response_str = response if isinstance(response, str) else safe_serialize(response)
                attributes[MessageAttributes.COMPLETION_CONTENT.format(i=0)] = response_str
                attributes[MessageAttributes.COMPLETION_ROLE.format(i=0)] = "assistant"
                attributes[WorkflowAttributes.FINAL_OUTPUT] = response_str
            
            span_kind = SpanKind.CLIENT
        
        # Ensure all spans have essential attributes - make sure we at least set the right prompt and completion
        # attributes so all spans are properly represented
        
        # For any span with input/prompt data, ensure gen_ai.prompt is set
        if hasattr(span_data, "input"):
            input_value = getattr(span_data, "input")
            prompt_str = input_value if isinstance(input_value, str) else safe_serialize(input_value)
            
            # Set prompt if not already set
            if SpanAttributes.LLM_PROMPTS not in attributes:
                attributes[SpanAttributes.LLM_PROMPTS] = prompt_str
                
            # Set workflow input if not already set
            if WorkflowAttributes.WORKFLOW_INPUT not in attributes:
                attributes[WorkflowAttributes.WORKFLOW_INPUT] = prompt_str
        
        # For any span with output/completion data, ensure gen_ai.completion attributes are set
        completion_content_attr = MessageAttributes.COMPLETION_CONTENT.format(i=0)
        if hasattr(span_data, "output") and completion_content_attr not in attributes:
            output_value = getattr(span_data, "output")
            self._set_completion_and_final_output(attributes, output_value)
        
        # If a span has final_output set but no completion content, use it
        if hasattr(span_data, "final_output") and completion_content_attr not in attributes:
            final_output = getattr(span_data, "final_output")
            self._set_completion_and_final_output(attributes, final_output)
        
        # Ensure agent spans have agent attributes
        if hasattr(span_data, "name") and AgentAttributes.AGENT_NAME not in attributes:
            attributes[AgentAttributes.AGENT_NAME] = getattr(span_data, "name")
            
        # Ensure LLM spans have system attribute
        if SpanAttributes.LLM_REQUEST_MODEL in attributes and SpanAttributes.LLM_SYSTEM not in attributes:
            attributes[SpanAttributes.LLM_SYSTEM] = "openai"
        
        return self._create_span(tracer, span_name, span_kind, attributes, span)
    
    def _create_span(self, tracer, span_name, span_kind, attributes, span):
        """Create an OpenTelemetry span from an Agents SDK span."""
        from opentelemetry import trace, context as context_api
        
        # Get span_id and trace_id from the original span for debugging
        orig_span_id = getattr(span, "span_id", "unknown")
        orig_trace_id = getattr(span, "trace_id", "unknown")
        
        # Store span parent ID for context linking
        parent_span_id = None
        if hasattr(span, "parent_id") and span.parent_id:
            parent_span_id = span.parent_id
            attributes["parent_span_id"] = parent_span_id
            logger.debug(f"Adding parent_span_id={parent_span_id} to span {span_name}")
        
        # Detailed debug logging of attributes being set on the span
        logger.debug(f"[OpenAIAgentsExporter] Creating OTel span from {orig_span_id}, trace={orig_trace_id}")
        
        # We need to track spans by their trace ID and organize their context relationships
        # Add original trace and span IDs as attributes for query/grouping
        if hasattr(span, "trace_id") and span.trace_id:
            attributes["agentops.original_trace_id"] = span.trace_id
            attributes["openai.agents.trace_id"] = span.trace_id
            
            if hasattr(span, "span_id") and span.span_id:
                attributes["agentops.original_span_id"] = span.span_id
                
            # Track if this is a root span (no parent) for later grouping
            if not parent_span_id:
                attributes["agentops.is_root_span"] = "true"
                
            # Create a consistent hash of the trace ID to help with grouping
            if span.trace_id.startswith("trace_"):
                try:
                    trace_hash = hash(span.trace_id) % 10000
                    attributes["agentops.trace_hash"] = str(trace_hash)
                    logger.debug(f"[OpenAIAgentsExporter] Using trace hash {trace_hash} for grouping")
                except Exception as e:
                    logger.error(f"[OpenAIAgentsExporter] Error creating trace hash: {e}")
        
        # Map parent-child relationships for responses
        if hasattr(span, "span_data") and span.span_data.__class__.__name__ == "ResponseSpanData" and parent_span_id:
            attributes["agentops.response_for_agent"] = parent_span_id
            attributes["agentops.parent_span_id"] = parent_span_id
        
        # Store the current context before we create a new span
        current_context = context_api.get_current()
        parent_context = None
        
        # If this is a child span, we need to find the parent span context to maintain trace continuity
        if parent_span_id:
            # Look for the parent span ID in our exporter's known spans
            # This allows us to properly establish parent-child relationships
            
            # For demonstration, log the attempt to link to parent
            logger.debug(f"[OpenAIAgentsExporter] Linking span {orig_span_id} to parent {parent_span_id}")
            
            # Set proper parent relationship in attributes since we can't modify the context directly
            attributes["agentops.parent_span_id"] = parent_span_id
        
        # Create the OpenTelemetry span with the current context
        # This ensures the span is properly linked to any active parent context
        otel_span = tracer.start_span(
            name=span_name, 
            kind=span_kind, 
            attributes=attributes
        )
        
        # Make this the current span
        context_api.attach(context_api.set_value("current-span", otel_span))
        
        # Log the created span's details
        if hasattr(otel_span, "context") and hasattr(otel_span.context, "span_id"):
            otel_span_id = f"{otel_span.context.span_id:x}"
            otel_trace_id = f"{otel_span.context.trace_id:x}"
            logger.debug(f"[OpenAIAgentsExporter] Created OTel span: {otel_span_id}, trace={otel_trace_id}")
            logger.debug(f"[OpenAIAgentsExporter] Original span: {orig_span_id}, trace={orig_trace_id}")
        
        # Handle errors if any
        if hasattr(span, "error") and span.error:
            otel_span.set_status(Status(StatusCode.ERROR))
            otel_span.record_exception(
                exception=Exception(span.error.get("message", "Unknown error")),
                attributes={"error.data": json.dumps(span.error.get("data", {}))},
            )
        
        # End the span to ensure it's exported
        otel_span.end()
        
        # Final debug log to verify span creation and ending
        logger.debug(f"[OpenAIAgentsExporter] Ended OTel span from {orig_span_id}")
        
        return otel_span
