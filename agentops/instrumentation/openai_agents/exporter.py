"""OpenAI Agents SDK Instrumentation Exporter for AgentOps"""
import json
from typing import Any, Dict

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

class AgentsDetailedExporter:
    """A detailed exporter for Agents SDK traces and spans that forwards them to AgentOps."""

    def __init__(self, tracer_provider=None):
        self.tracer_provider = tracer_provider
        
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
        if "output" not in response:
            return
            
        for i, item in enumerate(response["output"]):
            if "role" in item:
                attributes[MessageAttributes.COMPLETION_ROLE.format(i=i)] = item["role"]
            
            if "content" in item:
                content_items = item["content"]
                
                if isinstance(content_items, list):
                    texts = []
                    for content_item in content_items:
                        if content_item.get("type") == "output_text" and "text" in content_item:
                            texts.append(content_item["text"])
                    
                    attributes[MessageAttributes.COMPLETION_CONTENT.format(i=i)] = " ".join(texts)
                else:
                    attributes[MessageAttributes.COMPLETION_CONTENT.format(i=i)] = safe_serialize(content_items)
            
            if item.get("type") == "function_call":
                attributes[MessageAttributes.TOOL_CALL_ID.format(i=i, j=0)] = item.get("id", "")
                attributes[MessageAttributes.TOOL_CALL_NAME.format(i=i, j=0)] = item.get("name", "")
                attributes[MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=i, j=0)] = item.get("arguments", "{}")
            
            if "call_id" in item:
                if not attributes.get(MessageAttributes.TOOL_CALL_ID.format(i=i, j=0), ""):
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
                elif source_key in ("input", "output"):
                    attributes[target_attr] = safe_serialize(value)
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
            SpanAttributes.LLM_COMPLETIONS: "output",
            "gen_ai.completion": "output",
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
        
        if hasattr(span_data, "tools"):
            tools = getattr(span_data, "tools")
            if isinstance(tools, list) and tools is not None:
                attributes[AgentAttributes.AGENT_TOOLS] = ",".join(tools)
            else:
                logger.debug(f"Got Function tools in an unexpected format: {type(tools)}")
        
        return SpanKind.CLIENT
        
    def _process_generation_span(self, span: Any, span_data: Any, attributes: Dict[str, Any]) -> SpanKind:
        field_mapping = {
            SpanAttributes.LLM_REQUEST_MODEL: "model",
        }
        
        for target_attr, source_key in field_mapping.items():
            if hasattr(span_data, source_key):
                attributes[target_attr] = getattr(span_data, source_key)
                
        if SpanAttributes.LLM_REQUEST_MODEL in attributes:
            attributes[SpanAttributes.LLM_SYSTEM] = "openai"
        
        if hasattr(span_data, "model_config"):
            self._process_model_config(span_data.model_config, attributes)
        
        if hasattr(span_data, "output"):
            output = span_data.output
            
            response_dict = model_to_dict(output)
            
            if response_dict:
                self._process_response_metadata(response_dict, attributes)
                
                if "usage" in response_dict:
                    self._process_extended_token_usage(response_dict["usage"], attributes)
                
                self._process_completions(response_dict, attributes)
            else:
                attributes[SpanAttributes.LLM_COMPLETIONS] = safe_serialize(output)
        
        if hasattr(span_data, "usage"):
            self._process_extended_token_usage(span_data.usage, attributes)
            
        return SpanKind.CLIENT

    def export(self, items: list[Any]) -> None:
        for item in items:
            if hasattr(item, "spans"):
                self._export_trace(item)
            else:
                self._export_span(item)

    def _export_trace(self, trace: Any) -> None:
        tracer = get_tracer(LIBRARY_NAME, LIBRARY_VERSION, self.tracer_provider)

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
            if hasattr(trace, "group_id") and trace.group_id:
                span.set_attribute(CoreAttributes.GROUP_ID, trace.group_id)

    def _export_span(self, span: Any) -> None:
        tracer = get_tracer(LIBRARY_NAME, LIBRARY_VERSION, self.tracer_provider)

        span_data = span.span_data
        span_type = span_data.__class__.__name__

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
        
        return self._create_span(tracer, span_name, span_kind, attributes, span)
    
    def _create_span(self, tracer, span_name, span_kind, attributes, span):
        with tracer.start_as_current_span(name=span_name, kind=span_kind, attributes=attributes) as otel_span:
            if hasattr(span, "error") and span.error:
                otel_span.set_status(Status(StatusCode.ERROR))
                otel_span.record_exception(
                    exception=Exception(span.error.get("message", "Unknown error")),
                    attributes={"error.data": json.dumps(span.error.get("data", {}))},
                )
