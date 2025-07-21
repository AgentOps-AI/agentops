"""Responses API wrapper for OpenAI instrumentation.

This module provides attribute extraction for OpenAI Responses API endpoints.
"""

import json
import logging
from typing import Any, Dict, Optional, Tuple

from agentops.instrumentation.providers.openai.utils import is_openai_v1
from agentops.instrumentation.providers.openai.wrappers.shared import (
    model_as_dict,
    should_send_prompts,
)
from agentops.instrumentation.common.attributes import AttributeMap
from agentops.semconv import SpanAttributes, LLMRequestTypeValues

logger = logging.getLogger(__name__)


def handle_responses_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract attributes from responses API calls."""
    attributes = {
        SpanAttributes.LLM_SYSTEM: "OpenAI",
        SpanAttributes.LLM_REQUEST_TYPE: LLMRequestTypeValues.CHAT.value,
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

        # Input messages
        if should_send_prompts() and "input" in kwargs:
            messages = kwargs["input"]
            for i, msg in enumerate(messages):
                prefix = f"{SpanAttributes.LLM_PROMPTS}.{i}"
                if isinstance(msg, dict):
                    if "role" in msg:
                        attributes[f"{prefix}.role"] = msg["role"]
                    if "content" in msg:
                        content = msg["content"]
                        if isinstance(content, list):
                            content = json.dumps(content)
                        attributes[f"{prefix}.content"] = content

        # Tools
        if "tools" in kwargs:
            tools = kwargs["tools"]
            if tools:
                for i, tool in enumerate(tools):
                    if isinstance(tool, dict) and "function" in tool:
                        function = tool["function"]
                        prefix = f"{SpanAttributes.LLM_REQUEST_FUNCTIONS}.{i}"
                        if "name" in function:
                            attributes[f"{prefix}.name"] = function["name"]
                        if "description" in function:
                            attributes[f"{prefix}.description"] = function["description"]
                        if "parameters" in function:
                            attributes[f"{prefix}.parameters"] = json.dumps(function["parameters"])

    # Extract response attributes from return value
    if return_value:
        # Convert to dict if needed
        response_dict = {}
        if hasattr(return_value, "__dict__") and not hasattr(return_value, "__iter__"):
            response_dict = model_as_dict(return_value)
        elif isinstance(return_value, dict):
            response_dict = return_value
        elif hasattr(return_value, "model_dump"):
            response_dict = return_value.model_dump()

        # Basic response attributes
        if "id" in response_dict:
            attributes[SpanAttributes.LLM_RESPONSE_ID] = response_dict["id"]
        if "model" in response_dict:
            attributes[SpanAttributes.LLM_RESPONSE_MODEL] = response_dict["model"]

        # Usage
        usage = response_dict.get("usage", {})
        if usage:
            if is_openai_v1() and hasattr(usage, "__dict__"):
                usage = usage.__dict__
            if "total_tokens" in usage:
                attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = usage["total_tokens"]
            # Responses API uses input_tokens/output_tokens instead of prompt_tokens/completion_tokens
            if "input_tokens" in usage:
                attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = usage["input_tokens"]
            if "output_tokens" in usage:
                attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = usage["output_tokens"]

            # Reasoning tokens
            output_details = usage.get("output_tokens_details", {})
            if isinstance(output_details, dict) and "reasoning_tokens" in output_details:
                attributes[SpanAttributes.LLM_USAGE_REASONING_TOKENS] = output_details["reasoning_tokens"]

        # Output items
        if should_send_prompts() and "output" in response_dict:
            output_items = response_dict["output"]
            completion_idx = 0
            for i, output_item in enumerate(output_items):
                # Handle dictionary format
                if isinstance(output_item, dict):
                    item_type = output_item.get("type")
                # Handle object format (Pydantic models)
                elif hasattr(output_item, "type"):
                    item_type = output_item.type
                    output_item_dict = model_as_dict(output_item)
                    if output_item_dict and isinstance(output_item_dict, dict):
                        output_item = output_item_dict
                    else:
                        continue
                else:
                    continue

                if item_type == "message":
                    # Extract message content
                    if isinstance(output_item, dict):
                        content = output_item.get("content", [])
                        if isinstance(content, list):
                            # Aggregate all text content
                            text_parts = []
                            for content_item in content:
                                if isinstance(content_item, dict) and content_item.get("type") == "text":
                                    text = content_item.get("text", "")
                                    if text:
                                        text_parts.append(text)
                            if text_parts:
                                full_text = "".join(text_parts)
                                attributes[f"{SpanAttributes.LLM_COMPLETIONS}.{completion_idx}.content"] = full_text
                                attributes[f"{SpanAttributes.LLM_COMPLETIONS}.{completion_idx}.role"] = "assistant"
                                completion_idx += 1
                        elif isinstance(content, str):
                            # Simple string content
                            attributes[f"{SpanAttributes.LLM_COMPLETIONS}.{completion_idx}.content"] = content
                            attributes[f"{SpanAttributes.LLM_COMPLETIONS}.{completion_idx}.role"] = "assistant"
                            completion_idx += 1

                elif item_type == "function_call" and isinstance(output_item, dict):
                    # Handle function calls
                    # The arguments contain the actual response content for function calls
                    args_str = output_item.get("arguments", "")
                    if args_str:
                        try:
                            args = json.loads(args_str)
                            # Extract reasoning if present (common in o3 models)
                            reasoning = args.get("reasoning", "")
                            if reasoning:
                                attributes[f"{SpanAttributes.LLM_COMPLETIONS}.{completion_idx}.content"] = reasoning
                                attributes[f"{SpanAttributes.LLM_COMPLETIONS}.{completion_idx}.role"] = "assistant"
                                completion_idx += 1
                        except json.JSONDecodeError:
                            pass

                    # Also store tool call details
                    attributes[f"{SpanAttributes.LLM_COMPLETIONS}.{i}.tool_calls.0.id"] = output_item.get("id", "")
                    attributes[f"{SpanAttributes.LLM_COMPLETIONS}.{i}.tool_calls.0.name"] = output_item.get("name", "")
                    attributes[f"{SpanAttributes.LLM_COMPLETIONS}.{i}.tool_calls.0.arguments"] = args_str

                elif item_type == "reasoning" and isinstance(output_item, dict):
                    # Handle reasoning items (o3 models provide these)
                    summary = output_item.get("summary", "")
                    if summary:
                        attributes[f"{SpanAttributes.LLM_COMPLETIONS}.{completion_idx}.content"] = summary
                        attributes[f"{SpanAttributes.LLM_COMPLETIONS}.{completion_idx}.role"] = "assistant"
                        attributes[f"{SpanAttributes.LLM_COMPLETIONS}.{completion_idx}.type"] = "reasoning"
                        completion_idx += 1

    return attributes
