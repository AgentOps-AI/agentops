"""Assistant API wrapper for OpenAI instrumentation.

This module provides attribute extraction for OpenAI Assistant API endpoints.
"""

import json
import logging
from typing import Any, Dict, Optional, Tuple

from agentops.instrumentation.providers.openai.utils import is_openai_v1
from agentops.instrumentation.providers.openai.wrappers.shared import (
    model_as_dict,
    should_send_prompts,
)
from agentops.instrumentation.providers.openai.config import Config
from agentops.instrumentation.common.attributes import AttributeMap
from agentops.semconv import SpanAttributes

logger = logging.getLogger(__name__)


def handle_assistant_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract attributes from assistant creation calls."""
    attributes = {
        SpanAttributes.LLM_SYSTEM: "OpenAI",
        "gen_ai.operation.name": "assistant.create",
    }

    # Extract request attributes from kwargs
    if kwargs:
        if "model" in kwargs:
            attributes[SpanAttributes.LLM_REQUEST_MODEL] = kwargs["model"]
        if "name" in kwargs:
            attributes["gen_ai.assistant.name"] = kwargs["name"]
        if "description" in kwargs:
            attributes["gen_ai.assistant.description"] = kwargs["description"]
        if "instructions" in kwargs:
            attributes["gen_ai.assistant.instructions"] = kwargs["instructions"]

        # Tools
        tools = kwargs.get("tools", [])
        for i, tool in enumerate(tools):
            if isinstance(tool, dict):
                attributes[f"gen_ai.assistant.tools.{i}.type"] = tool.get("type")
            else:
                attributes[f"gen_ai.assistant.tools.{i}.type"] = str(tool)

    # Extract response attributes
    if return_value:
        response_dict = {}
        if hasattr(return_value, "__dict__"):
            response_dict = model_as_dict(return_value)
        elif isinstance(return_value, dict):
            response_dict = return_value

        if "id" in response_dict:
            attributes["gen_ai.assistant.id"] = response_dict["id"]
        if "model" in response_dict:
            attributes[SpanAttributes.LLM_RESPONSE_MODEL] = response_dict["model"]
        if "created_at" in response_dict:
            attributes["gen_ai.assistant.created_at"] = response_dict["created_at"]

        if Config.enrich_assistant:
            if "object" in response_dict:
                attributes["gen_ai.assistant.object"] = response_dict["object"]
            if "file_ids" in response_dict:
                attributes["gen_ai.assistant.file_ids"] = json.dumps(response_dict["file_ids"])
            if "metadata" in response_dict:
                attributes["gen_ai.assistant.metadata"] = json.dumps(response_dict["metadata"])

    return attributes


def handle_run_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract attributes from run creation calls."""
    attributes = {
        SpanAttributes.LLM_SYSTEM: "OpenAI",
        "gen_ai.operation.name": "run.create",
    }

    # Extract request attributes from kwargs
    if kwargs:
        if "thread_id" in kwargs:
            attributes["gen_ai.thread.id"] = kwargs["thread_id"]
        if "assistant_id" in kwargs:
            attributes["gen_ai.assistant.id"] = kwargs["assistant_id"]
        if "model" in kwargs:
            attributes[SpanAttributes.LLM_REQUEST_MODEL] = kwargs["model"]
        if "instructions" in kwargs:
            attributes["gen_ai.run.instructions"] = kwargs["instructions"]

        # Additional messages
        additional_messages = kwargs.get("additional_messages", [])
        if additional_messages and should_send_prompts():
            for i, msg in enumerate(additional_messages):
                prefix = f"gen_ai.run.additional_messages.{i}"
                if "role" in msg:
                    attributes[f"{prefix}.role"] = msg["role"]
                if "content" in msg:
                    attributes[f"{prefix}.content"] = msg["content"]

    # Extract response attributes
    if return_value:
        response_dict = {}
        if hasattr(return_value, "__dict__"):
            response_dict = model_as_dict(return_value)
        elif isinstance(return_value, dict):
            response_dict = return_value

        if "id" in response_dict:
            attributes["gen_ai.run.id"] = response_dict["id"]
        if "status" in response_dict:
            attributes["gen_ai.run.status"] = response_dict["status"]
        if "thread_id" in response_dict:
            attributes["gen_ai.thread.id"] = response_dict["thread_id"]
        if "assistant_id" in response_dict:
            attributes["gen_ai.assistant.id"] = response_dict["assistant_id"]
        if "model" in response_dict:
            attributes[SpanAttributes.LLM_RESPONSE_MODEL] = response_dict["model"]

        # Usage
        usage = response_dict.get("usage", {})
        if usage:
            if is_openai_v1() and hasattr(usage, "__dict__"):
                usage = usage.__dict__
            if "prompt_tokens" in usage:
                attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = usage["prompt_tokens"]
            if "completion_tokens" in usage:
                attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = usage["completion_tokens"]
            if "total_tokens" in usage:
                attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = usage["total_tokens"]

        if Config.enrich_assistant:
            if "created_at" in response_dict:
                attributes["gen_ai.run.created_at"] = response_dict["created_at"]
            if "started_at" in response_dict:
                attributes["gen_ai.run.started_at"] = response_dict["started_at"]
            if "completed_at" in response_dict:
                attributes["gen_ai.run.completed_at"] = response_dict["completed_at"]
            if "failed_at" in response_dict:
                attributes["gen_ai.run.failed_at"] = response_dict["failed_at"]
            if "metadata" in response_dict:
                attributes["gen_ai.run.metadata"] = json.dumps(response_dict["metadata"])

    return attributes


def handle_run_retrieve_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract attributes from run retrieval calls."""
    attributes = {
        SpanAttributes.LLM_SYSTEM: "OpenAI",
        "gen_ai.operation.name": "run.retrieve",
    }

    # Extract run_id from args or kwargs
    run_id = None
    if args and len(args) > 0:
        run_id = args[0]
    elif kwargs:
        run_id = kwargs.get("run_id")

    if run_id:
        attributes["gen_ai.run.id"] = run_id

    # Response attributes are same as run creation
    if return_value:
        response_attrs = handle_run_attributes(None, None, return_value)
        # Update with response attributes but keep our operation name
        response_attrs.pop("gen_ai.operation.name", None)
        attributes.update(response_attrs)

    return attributes


def handle_run_stream_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract attributes from run create_and_stream calls."""
    attributes = {
        SpanAttributes.LLM_SYSTEM: "OpenAI",
        "gen_ai.operation.name": "run.create_and_stream",
        SpanAttributes.LLM_REQUEST_STREAMING: True,
    }

    # Request attributes are same as run creation
    if kwargs:
        request_attrs = handle_run_attributes(None, kwargs, None)
        # Update with request attributes but keep our operation name
        request_attrs.pop("gen_ai.operation.name", None)
        attributes.update(request_attrs)

    # For streaming, we don't have immediate response attributes

    return attributes


def handle_messages_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract attributes from messages list calls."""
    attributes = {
        SpanAttributes.LLM_SYSTEM: "OpenAI",
        "gen_ai.operation.name": "messages.list",
    }

    # Extract thread_id
    thread_id = None
    if args and len(args) > 0:
        thread_id = args[0]
    elif kwargs:
        thread_id = kwargs.get("thread_id")

    if thread_id:
        attributes["gen_ai.thread.id"] = thread_id

    # Extract response attributes
    if return_value:
        response_dict = {}
        if hasattr(return_value, "__dict__"):
            response_dict = model_as_dict(return_value)
        elif isinstance(return_value, dict):
            response_dict = return_value

        # For list responses, note the count
        data = response_dict.get("data", [])
        attributes["gen_ai.messages.count"] = len(data)

        if Config.enrich_assistant and should_send_prompts():
            # Include details of first few messages
            for i, msg in enumerate(data[:10]):  # Limit to first 10
                if isinstance(msg, dict):
                    msg_dict = msg
                else:
                    msg_dict = model_as_dict(msg)

                prefix = f"gen_ai.messages.{i}"
                if "id" in msg_dict:
                    attributes[f"{prefix}.id"] = msg_dict["id"]
                if "role" in msg_dict:
                    attributes[f"{prefix}.role"] = msg_dict["role"]
                if "created_at" in msg_dict:
                    attributes[f"{prefix}.created_at"] = msg_dict["created_at"]

                # Handle content
                content = msg_dict.get("content", [])
                if content and isinstance(content, list):
                    for j, content_item in enumerate(content):
                        try:
                            if isinstance(content_item, dict) and content_item.get("type") == "text":
                                text_obj = content_item.get("text")
                                if text_obj and isinstance(text_obj, dict):
                                    text_value = text_obj.get("value", "")
                                    attributes[f"{prefix}.content.{j}"] = text_value
                            elif hasattr(content_item, "text") and hasattr(content_item.text, "value"):
                                # Handle object-style content
                                attributes[f"{prefix}.content.{j}"] = content_item.text.value
                        except Exception:
                            # Continue processing other content items
                            continue

    return attributes
