"""Chat completions wrapper for OpenAI instrumentation.

This module provides attribute extraction for OpenAI chat completions API,
compatible with the common wrapper pattern.
"""

import json
import logging
from typing import Any, Dict, Optional, Tuple

from opentelemetry.trace import Span

from agentops.instrumentation.providers.openai.utils import is_openai_v1
from agentops.instrumentation.providers.openai.wrappers.shared import (
    model_as_dict,
    should_send_prompts,
)
from agentops.instrumentation.common.attributes import AttributeMap
from agentops.semconv import SpanAttributes, LLMRequestTypeValues
from agentops.semconv.tool import ToolAttributes
from agentops.semconv.span_kinds import AgentOpsSpanKindValues

from opentelemetry import context as context_api
from opentelemetry.trace import SpanKind, Status, StatusCode, get_tracer

logger = logging.getLogger(__name__)

LLM_REQUEST_TYPE = LLMRequestTypeValues.CHAT


def _create_tool_span(parent_span, tool_call_data):
    """
    Create a distinct span for each tool call.

    Args:
        parent_span: The parent LLM span
        tool_call_data: The tool call data dictionary
    """
    # Get the tracer for this module
    tracer = get_tracer(__name__)

    # Create a child span for the tool call
    with tracer.start_as_current_span(
        name=f"tool_call.{tool_call_data['function']['name']}",
        kind=SpanKind.INTERNAL,
        context=context_api.set_value("current_span", parent_span),
    ) as tool_span:
        # Set the span kind to TOOL
        tool_span.set_attribute("agentops.span.kind", AgentOpsSpanKindValues.TOOL)

        # Set tool-specific attributes
        tool_span.set_attribute(ToolAttributes.TOOL_NAME, tool_call_data["function"]["name"])
        tool_span.set_attribute(ToolAttributes.TOOL_PARAMETERS, tool_call_data["function"]["arguments"])
        tool_span.set_attribute("tool.call.id", tool_call_data["id"])
        tool_span.set_attribute("tool.call.type", tool_call_data["type"])

        # Set status to OK for successful tool call creation
        tool_span.set_status(Status(StatusCode.OK))


def handle_chat_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
    span: Optional[Span] = None,
) -> AttributeMap:
    """Extract attributes from chat completion calls.

    This function is designed to work with the common wrapper pattern,
    extracting attributes from the method arguments and return value.

    Args:
        args: Method arguments (not used in this implementation)
        kwargs: Method keyword arguments
        return_value: Method return value
        span: The parent span for creating tool spans
    """
    attributes = {
        SpanAttributes.LLM_REQUEST_TYPE: LLM_REQUEST_TYPE.value,
        SpanAttributes.LLM_SYSTEM: "OpenAI",
    }

    # Extract request attributes from kwargs
    if kwargs:
        # Model
        if "model" in kwargs:
            attributes[SpanAttributes.LLM_REQUEST_MODEL] = kwargs["model"]

        # Request parameters
        if "max_tokens" in kwargs:
            attributes[SpanAttributes.LLM_REQUEST_MAX_TOKENS] = kwargs["max_tokens"]
        if "temperature" in kwargs:
            attributes[SpanAttributes.LLM_REQUEST_TEMPERATURE] = kwargs["temperature"]
        if "top_p" in kwargs:
            attributes[SpanAttributes.LLM_REQUEST_TOP_P] = kwargs["top_p"]
        if "frequency_penalty" in kwargs:
            attributes[SpanAttributes.LLM_REQUEST_FREQUENCY_PENALTY] = kwargs["frequency_penalty"]
        if "presence_penalty" in kwargs:
            attributes[SpanAttributes.LLM_REQUEST_PRESENCE_PENALTY] = kwargs["presence_penalty"]
        if "user" in kwargs:
            attributes[SpanAttributes.LLM_USER] = kwargs["user"]

        # Streaming
        attributes[SpanAttributes.LLM_REQUEST_STREAMING] = kwargs.get("stream", False)

        # Headers
        headers = kwargs.get("extra_headers") or kwargs.get("headers")
        if headers:
            attributes[SpanAttributes.LLM_REQUEST_HEADERS] = str(headers)

        # Messages
        if should_send_prompts() and "messages" in kwargs:
            messages = kwargs["messages"]
            for i, msg in enumerate(messages):
                prefix = f"{SpanAttributes.LLM_PROMPTS}.{i}"
                if "role" in msg:
                    attributes[f"{prefix}.role"] = msg["role"]
                if "content" in msg:
                    content = msg["content"]
                    if isinstance(content, list):
                        # Handle multi-modal content
                        content = json.dumps(content)
                    attributes[f"{prefix}.content"] = content
                if "tool_call_id" in msg:
                    attributes[f"{prefix}.tool_call_id"] = msg["tool_call_id"]

                # Tool calls
                if "tool_calls" in msg:
                    tool_calls = msg["tool_calls"]
                    if tool_calls:  # Check if tool_calls is not None
                        for j, tool_call in enumerate(tool_calls):
                            if is_openai_v1() and hasattr(tool_call, "__dict__"):
                                tool_call = model_as_dict(tool_call)
                            function = tool_call.get("function", {})
                            attributes[f"{prefix}.tool_calls.{j}.id"] = tool_call.get("id")
                            attributes[f"{prefix}.tool_calls.{j}.name"] = function.get("name")
                            attributes[f"{prefix}.tool_calls.{j}.arguments"] = function.get("arguments")

        # Functions
        if "functions" in kwargs:
            functions = kwargs["functions"]
            for i, function in enumerate(functions):
                prefix = f"{SpanAttributes.LLM_REQUEST_FUNCTIONS}.{i}"
                attributes[f"{prefix}.name"] = function.get("name")
                attributes[f"{prefix}.description"] = function.get("description")
                attributes[f"{prefix}.parameters"] = json.dumps(function.get("parameters"))

        # Tools
        if "tools" in kwargs:
            tools = kwargs["tools"]
            if tools:  # Check if tools is not None
                for i, tool in enumerate(tools):
                    function = tool.get("function", {})
                    prefix = f"{SpanAttributes.LLM_REQUEST_FUNCTIONS}.{i}"
                    attributes[f"{prefix}.name"] = function.get("name")
                    attributes[f"{prefix}.description"] = function.get("description")
                    attributes[f"{prefix}.parameters"] = json.dumps(function.get("parameters"))

    # Extract response attributes from return value
    if return_value:
        # Note: For streaming responses, return_value might be a generator/stream
        # In that case, we won't have the full response data here

        # Convert to dict if needed
        response_dict = {}
        if hasattr(return_value, "__dict__") and not hasattr(return_value, "__iter__"):
            response_dict = model_as_dict(return_value)
        elif isinstance(return_value, dict):
            response_dict = return_value
        elif hasattr(return_value, "model_dump"):
            # Handle Pydantic models directly
            response_dict = return_value.model_dump()
        elif hasattr(return_value, "__dict__"):
            # Try to use model_as_dict even if it has __iter__(fallback)
            response_dict = model_as_dict(return_value)

        logger.debug(f"[OPENAI DEBUG] response_dict keys: {list(response_dict.keys()) if response_dict else 'empty'}")

        # Basic response attributes
        if "id" in response_dict:
            attributes[SpanAttributes.LLM_RESPONSE_ID] = response_dict["id"]
        if "model" in response_dict:
            attributes[SpanAttributes.LLM_RESPONSE_MODEL] = response_dict["model"]
        if "system_fingerprint" in response_dict and response_dict["system_fingerprint"] is not None:
            attributes[SpanAttributes.LLM_OPENAI_RESPONSE_SYSTEM_FINGERPRINT] = response_dict["system_fingerprint"]

        # Usage
        usage = response_dict.get("usage", {})
        if usage:
            if is_openai_v1() and hasattr(usage, "__dict__"):
                usage = usage.__dict__
            if "total_tokens" in usage:
                attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = usage["total_tokens"]
            if "prompt_tokens" in usage:
                attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = usage["prompt_tokens"]
            if "completion_tokens" in usage:
                attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = usage["completion_tokens"]

            # Reasoning tokens
            output_details = usage.get("output_tokens_details", {})
            if isinstance(output_details, dict) and "reasoning_tokens" in output_details:
                attributes[SpanAttributes.LLM_USAGE_REASONING_TOKENS] = output_details["reasoning_tokens"]

        # Choices
        if should_send_prompts() and "choices" in response_dict:
            choices = response_dict["choices"]
            for choice in choices:
                index = choice.get("index", 0)
                prefix = f"{SpanAttributes.LLM_COMPLETIONS}.{index}"

                if "finish_reason" in choice:
                    attributes[f"{prefix}.finish_reason"] = choice["finish_reason"]

                # Content filter
                if "content_filter_results" in choice:
                    attributes[f"{prefix}.content_filter_results"] = json.dumps(choice["content_filter_results"])

                # Message
                message = choice.get("message", {})
                if message:
                    if "role" in message:
                        attributes[f"{prefix}.role"] = message["role"]
                    if "content" in message and message["content"] is not None:
                        attributes[f"{prefix}.content"] = message["content"]
                    if "refusal" in message and message["refusal"] is not None:
                        attributes[f"{prefix}.refusal"] = message["refusal"]

                    # Function call
                    if "function_call" in message:
                        function_call = message["function_call"]
                        if function_call:  # Check if function_call is not None
                            attributes[f"{prefix}.tool_calls.0.name"] = function_call.get("name")
                            attributes[f"{prefix}.tool_calls.0.arguments"] = function_call.get("arguments")

                    # Tool calls
                    if "tool_calls" in message:
                        tool_calls = message["tool_calls"]
                        if tool_calls and span is not None:
                            for i, tool_call in enumerate(tool_calls):
                                # Convert tool_call to the format expected by _create_tool_span
                                function = tool_call.get("function", {})
                                tool_call_data = {
                                    "id": tool_call.get("id", ""),
                                    "type": tool_call.get("type", "function"),
                                    "function": {
                                        "name": function.get("name", ""),
                                        "arguments": function.get("arguments", ""),
                                    },
                                }
                                # Create a child span for this tool call
                                _create_tool_span(span, tool_call_data)

        # Prompt filter results
        if "prompt_filter_results" in response_dict:
            attributes[f"{SpanAttributes.LLM_PROMPTS}.prompt_filter_results"] = json.dumps(
                response_dict["prompt_filter_results"]
            )

    return attributes
