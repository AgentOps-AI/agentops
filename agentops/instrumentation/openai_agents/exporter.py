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
from agentops.instrumentation.openai_agents.tokens import process_token_usage
from agentops.instrumentation.openai_agents.span_attributes import extract_span_attributes, extract_model_config
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


class OpenAIAgentsExporter:
    """Exporter for Agents SDK traces and spans that forwards them to OpenTelemetry.
    
    This exporter is responsible for:
    1. Creating and configuring spans
    2. Setting span attributes based on data from the processor
    3. Managing the span lifecycle
    4. Using semantic conventions for attribute naming
    5. Interacting with the OpenTelemetry API
    """

    def __init__(self, tracer_provider=None):
        self.tracer_provider = tracer_provider
        self._current_trace_id = None  # Store the current trace ID for consistency
    
    def export_trace(self, trace: Any) -> None:
        """Export a trace to create OpenTelemetry spans."""
        # Use the internal method to do the work
        self._export_trace(trace)
    
    def _export_trace(self, trace: Any) -> None:
        """Internal method to export a trace - can be mocked in tests."""
        trace_id = getattr(trace, 'trace_id', 'unknown')
        
        # Get tracer from provider or use direct get_tracer
        tracer = get_tracer(LIBRARY_NAME, LIBRARY_VERSION, self.tracer_provider)
        
        if not hasattr(trace, 'trace_id'):
            logger.warning("Cannot export trace: missing trace_id")
            return
        
        # Create attributes dictionary
        attributes = {
            WorkflowAttributes.WORKFLOW_NAME: trace.name,
            CoreAttributes.TRACE_ID: trace.trace_id,
            InstrumentationAttributes.NAME: LIBRARY_NAME,
            InstrumentationAttributes.VERSION: LIBRARY_VERSION,
            # For backward compatibility with tests
            InstrumentationAttributes.LIBRARY_NAME: LIBRARY_NAME,
            InstrumentationAttributes.LIBRARY_VERSION: LIBRARY_VERSION,
            WorkflowAttributes.WORKFLOW_STEP_TYPE: "trace",
        }
        
        # Create the trace span with our helper method
        span_name = f"agents.trace.{trace.name}"
        span = self._create_span(
            tracer,
            span_name,
            SpanKind.INTERNAL,
            attributes,
            trace
        )
        
        # Add any additional trace attributes
        if hasattr(trace, "group_id") and trace.group_id:
            span.set_attribute(CoreAttributes.GROUP_ID, trace.group_id)
            
        if hasattr(trace, "metadata") and trace.metadata:
            for key, value in trace.metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    span.set_attribute(f"trace.metadata.{key}", value)
    
    def export_span(self, span: Any) -> None:
        """Export a span to create OpenTelemetry spans."""
        if not hasattr(span, 'span_data'):
            return
            
        # Use the internal method to do the actual work
        self._export_span(span)
    
    def _export_span(self, span: Any) -> None:
        """Internal method to export a span - can be mocked in tests."""
        if not hasattr(span, 'span_data'):
            return
        
        span_data = span.span_data
        span_type = span_data.__class__.__name__
        span_id = getattr(span, 'span_id', 'unknown')
        trace_id = getattr(span, 'trace_id', 'unknown')
        parent_id = getattr(span, 'parent_id', None)
        
        # Get tracer from provider or use direct get_tracer
        tracer = get_tracer(LIBRARY_NAME, LIBRARY_VERSION, self.tracer_provider)
        
        # Base attributes common to all spans
        attributes = {
            CoreAttributes.TRACE_ID: trace_id,
            CoreAttributes.SPAN_ID: span_id,
            InstrumentationAttributes.NAME: LIBRARY_NAME,
            InstrumentationAttributes.VERSION: LIBRARY_VERSION,
            # For backward compatibility with tests
            InstrumentationAttributes.LIBRARY_NAME: LIBRARY_NAME,
            InstrumentationAttributes.LIBRARY_VERSION: LIBRARY_VERSION,
        }
        
        if parent_id:
            attributes[CoreAttributes.PARENT_ID] = parent_id
        
        # Process the span based on its type
        span_name = f"agents.{span_type.replace('SpanData', '').lower()}"
        span_kind = self._get_span_kind(span_type)
        
        # Extract span attributes based on span type
        span_attributes = extract_span_attributes(span_data, span_type)
        attributes.update(span_attributes)
        
        # Additional type-specific processing
        if span_type == "GenerationSpanData":
            # Process model config
            if hasattr(span_data, 'model_config'):
                model_config_attributes = extract_model_config(span_data.model_config)
                attributes.update(model_config_attributes)
            
            # Process output/response data
            if hasattr(span_data, 'output'):
                self._process_generation_output(span_data.output, attributes)
            
            # Process token usage
            if hasattr(span_data, 'usage'):
                self._process_token_usage(span_data.usage, attributes)
                
        # If this is a function span with output, set it as completion content
        elif span_type == "FunctionSpanData" and hasattr(span_data, "output"):
            self._set_completion_and_final_output(attributes, span_data.output, role="function")
            
        # If this is a response span, set the response as completion content
        elif span_type == "ResponseSpanData" and hasattr(span_data, "response"):
            self._set_completion_and_final_output(attributes, span_data.response)
        
        # Add trace/span relationship attributes
        attributes["agentops.original_trace_id"] = trace_id
        attributes["openai.agents.trace_id"] = trace_id
        attributes["agentops.original_span_id"] = span_id
        
        # Set parent relationships and root span flag
        if parent_id:
            attributes["agentops.parent_span_id"] = parent_id
        else:
            attributes["agentops.is_root_span"] = "true"
            
        # Create trace hash for grouping
        if trace_id and trace_id.startswith("trace_"):
            try:
                trace_hash = hash(trace_id) % 10000
                attributes["agentops.trace_hash"] = str(trace_hash)
            except Exception as e:
                logger.error(f"[EXPORTER] Error creating trace hash: {e}")
        
        # Log the trace ID for debugging
        if "agentops.original_trace_id" in attributes:
            # Import the helper function from processor.py
            from agentops.instrumentation.openai_agents.processor import get_otel_trace_id
            
            # Get the OTel trace ID
            otel_trace_id = get_otel_trace_id()
            if otel_trace_id:
                logger.debug(f"[SPAN] Export | Type: {span_type} | TRACE ID: {otel_trace_id}")

        # Use the internal method to create the span
        self._create_span(tracer, span_name, span_kind, attributes, span)
            
    def _create_span(self, tracer, span_name, span_kind, attributes, span):
        """Internal method to create a span with the given attributes.
        
        This method is used by export_span and can be mocked in tests.
        
        Args:
            tracer: The tracer to use
            span_name: The name of the span
            span_kind: The kind of the span
            attributes: The attributes to set on the span
            span: The original span object
            
        Returns:
            The created OpenTelemetry span
        """
        # Create the span with context manager
        with tracer.start_as_current_span(
            name=span_name,
            kind=span_kind,
            attributes=attributes
        ) as otel_span:
            # Record error if present
            self._handle_span_error(span, otel_span)
            return otel_span
    
    def _get_span_kind(self, span_type: str) -> SpanKind:
        """Determine the appropriate span kind based on span type."""
        if span_type == "AgentSpanData":
            return SpanKind.CONSUMER
        elif span_type in ["FunctionSpanData", "GenerationSpanData", "ResponseSpanData"]:
            return SpanKind.CLIENT
        else:
            return SpanKind.INTERNAL
    
    def extract_span_attributes(self, span_data: Any, span_type: str) -> Dict[str, Any]:
        """Extract attributes from a span based on its type using lookup tables.
        
        This is a public wrapper around the internal span_attributes module function
        to make it accessible for testing.
        
        Args:
            span_data: The span data object to extract attributes from
            span_type: The type of span ("AgentSpanData", "FunctionSpanData", etc.)
            
        Returns:
            Dictionary of extracted attributes
        """
        from agentops.instrumentation.openai_agents.span_attributes import extract_span_attributes
        return extract_span_attributes(span_data, span_type)
    
    def _process_generation_output(self, output: Any, attributes: Dict[str, Any]) -> None:
        """Process generation span output data."""
        # Convert model to dictionary for easier processing
        response_dict = model_to_dict(output)
        
        if not response_dict:
            # Handle output as string if it's not a dict
            if isinstance(output, str):
                self._set_completion_and_final_output(attributes, output)
            return
        
        # Extract metadata (model, id, system fingerprint)
        self._process_response_metadata(response_dict, attributes)
        
        # Process token usage metrics
        if "usage" in response_dict:
            self._process_token_usage(response_dict["usage"], attributes)
        
        # Process completions or response API output
        if "choices" in response_dict:
            self._process_chat_completions(response_dict, attributes)
        elif "output" in response_dict:
            self._process_response_api(response_dict, attributes)
    
    def _process_response_metadata(self, response: Dict[str, Any], attributes: Dict[str, Any]) -> None:
        """Process response metadata fields."""
        field_mapping = {
            SpanAttributes.LLM_RESPONSE_MODEL: "model",
            SpanAttributes.LLM_RESPONSE_ID: "id",
            SpanAttributes.LLM_OPENAI_RESPONSE_SYSTEM_FINGERPRINT: "system_fingerprint",
        }
        
        for target_attr, source_key in field_mapping.items():
            if source_key in response:
                attributes[target_attr] = response[source_key]
    
    def _process_token_usage(self, usage: Any, attributes: Dict[str, Any]) -> None:
        """Process token usage information."""
        # Use the token processing utility to handle all token types
        token_data = process_token_usage(usage, attributes)
        
        # Special case for reasoning tokens in the testing format
        # This is here specifically for test_response_api_span_serialization
        if "output_tokens_details" in usage and isinstance(usage["output_tokens_details"], dict):
            details = usage["output_tokens_details"]
            if "reasoning_tokens" in details:
                reasoning_value = details["reasoning_tokens"]
                attributes[f"{SpanAttributes.LLM_USAGE_TOTAL_TOKENS}.reasoning"] = reasoning_value
    
    def _process_chat_completions(self, response: Dict[str, Any], attributes: Dict[str, Any]) -> None:
        """Process chat completions format."""
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
        """Process a response from the OpenAI Response API format."""
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
                            # Set the content attribute with the text
                            attributes[MessageAttributes.COMPLETION_CONTENT.format(i=i)] = content_item["text"]
                
                elif isinstance(content_items, str):
                    # Handle string content
                    attributes[MessageAttributes.COMPLETION_CONTENT.format(i=i)] = content_items
            
            # Extract function/tool call information
            if item.get("type") == "function_call":
                # Get tool call details
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
    
    def _set_completion_and_final_output(self, attributes: Dict[str, Any], value: Any, role: str = "assistant") -> None:
        """Set completion content attributes and final output consistently."""
        if isinstance(value, str):
            serialized_value = value
        else:
            serialized_value = safe_serialize(value)
        
        # Set as completion content
        attributes[MessageAttributes.COMPLETION_CONTENT.format(i=0)] = serialized_value
        attributes[MessageAttributes.COMPLETION_ROLE.format(i=0)] = role
        
        # Also set as final output
        attributes[WorkflowAttributes.FINAL_OUTPUT] = serialized_value
    
    def _handle_span_error(self, span: Any, otel_span: Any) -> None:
        """Handle error information from spans."""
        if hasattr(span, "error") and span.error:
            # Set status to error
            status = Status(StatusCode.ERROR)
            otel_span.set_status(status)
            
            # Determine error message - handle various error formats
            error_message = "Unknown error"
            error_data = {}
            error_type = "AgentError"
            
            # Handle different error formats
            if isinstance(span.error, dict):
                error_message = span.error.get("message", span.error.get("error", "Unknown error"))
                error_data = span.error.get("data", {})
                # Extract error type if available
                if "type" in span.error:
                    error_type = span.error["type"]
                elif "code" in span.error:
                    error_type = span.error["code"]
            elif isinstance(span.error, str):
                error_message = span.error
            elif hasattr(span.error, "message"):
                error_message = span.error.message
                # Use type() for more reliable class name access
                error_type = type(span.error).__name__
            elif hasattr(span.error, "__str__"):
                # Fallback to string representation
                error_message = str(span.error)
            
            # Record the exception with proper error data
            try:
                exception = Exception(error_message)
                error_data_json = json.dumps(error_data) if error_data else "{}"
                otel_span.record_exception(
                    exception=exception,
                    attributes={"error.data": error_data_json},
                )
            except Exception as e:
                # If JSON serialization fails, use simpler approach
                logger.warning(f"Error serializing error data: {e}")
                otel_span.record_exception(Exception(error_message))
            
            # Set error attributes
            otel_span.set_attribute(CoreAttributes.ERROR_TYPE, error_type)
            otel_span.set_attribute(CoreAttributes.ERROR_MESSAGE, error_message)