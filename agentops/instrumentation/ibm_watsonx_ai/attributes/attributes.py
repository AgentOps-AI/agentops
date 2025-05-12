"""Attributes for IBM watsonx.ai model instrumentation.

This module provides attribute extraction functions for IBM watsonx.ai model operations.
"""

from typing import Any, Dict, Optional, Tuple
from agentops.instrumentation.common.attributes import AttributeMap
from agentops.semconv import SpanAttributes, MessageAttributes
from agentops.instrumentation.ibm_watsonx_ai.attributes.common import (
    extract_params_attributes,
    convert_params_to_dict,
    extract_prompt_from_args,
    extract_messages_from_args,
    extract_params_from_args,
)


def get_generate_attributes(
    args: Optional[Tuple] = None, kwargs: Optional[Dict] = None, return_value: Optional[Any] = None
) -> AttributeMap:
    """Extract token usage attributes from generate method calls."""
    attributes = {}

    # Extract prompt using helper function
    prompt = extract_prompt_from_args(args, kwargs)
    if prompt:
        attributes[MessageAttributes.PROMPT_ROLE.format(i=0)] = "user"
        attributes[MessageAttributes.PROMPT_CONTENT.format(i=0)] = prompt
        attributes[MessageAttributes.PROMPT_TYPE.format(i=0)] = "text"

    # Extract parameters using helper functions
    params = extract_params_from_args(args, kwargs)
    if params:
        params_dict = convert_params_to_dict(params)
        if params_dict:
            attributes.update(extract_params_attributes(params_dict))

    # Extract response information
    if return_value:
        if isinstance(return_value, dict):
            # Extract model information
            if "model_id" in return_value:
                attributes[SpanAttributes.LLM_REQUEST_MODEL] = return_value["model_id"]

            # Handle results
            if "results" in return_value:
                for idx, result in enumerate(return_value["results"]):
                    # Extract completion
                    if "generated_text" in result:
                        attributes[MessageAttributes.COMPLETION_CONTENT.format(i=idx)] = result["generated_text"]
                        attributes[MessageAttributes.COMPLETION_ROLE.format(i=idx)] = "assistant"
                        attributes[MessageAttributes.COMPLETION_TYPE.format(i=idx)] = "text"

                    # Extract token usage
                    if "input_token_count" in result:
                        attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = result["input_token_count"]
                    if "generated_token_count" in result:
                        attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = result["generated_token_count"]
                    if "input_token_count" in result and "generated_token_count" in result:
                        attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = (
                            result["input_token_count"] + result["generated_token_count"]
                        )

                    if "stop_reason" in result:
                        attributes[SpanAttributes.LLM_RESPONSE_STOP_REASON] = result["stop_reason"]

    return attributes


def get_tokenize_attributes(
    args: Optional[Tuple] = None, kwargs: Optional[Dict] = None, return_value: Optional[Any] = None
) -> AttributeMap:
    """Extract attributes from tokenize method calls."""
    attributes = {}

    # Extract input from args or kwargs using helper function
    prompt = extract_prompt_from_args(args, kwargs)
    if prompt:
        attributes[MessageAttributes.PROMPT_ROLE.format(i=0)] = "user"
        attributes[MessageAttributes.PROMPT_CONTENT.format(i=0)] = prompt
        attributes[MessageAttributes.PROMPT_TYPE.format(i=0)] = "text"

    # Extract response information
    if return_value and isinstance(return_value, dict):
        if "model_id" in return_value:
            attributes[SpanAttributes.LLM_REQUEST_MODEL] = return_value["model_id"]
        if "result" in return_value:
            attributes["ibm.watsonx.tokenize.result"] = str(return_value["result"])
            if "token_count" in return_value["result"]:
                attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = return_value["result"]["token_count"]

    return attributes


def get_model_details_attributes(
    args: Optional[Tuple] = None, kwargs: Optional[Dict] = None, return_value: Optional[Any] = None
) -> AttributeMap:
    """Extract attributes from get_details method calls."""
    if not isinstance(return_value, dict):
        return {}

    # Basic model information
    attributes = {
        f"ibm.watsonx.model.{key}": value
        for key, value in return_value.items()
        if key
        in [
            "model_id",
            "label",
            "provider",
            "source",
            "short_description",
            "long_description",
            "number_params",
            "input_tier",
            "output_tier",
        ]
    }

    # Model functions
    if "functions" in return_value:
        attributes["ibm.watsonx.model.functions"] = str([func["id"] for func in return_value["functions"]])

    # Model tasks
    if "tasks" in return_value:
        task_info = [
            {k: v for k, v in task.items() if k in ["id", "ratings", "tags"]} for task in return_value["tasks"]
        ]
        attributes["ibm.watsonx.model.tasks"] = str(task_info)

    # Model limits
    if "model_limits" in return_value:
        limits = return_value["model_limits"]
        attributes.update(
            {
                f"ibm.watsonx.model.{key}": value
                for key, value in limits.items()
                if key in ["max_sequence_length", "max_output_tokens", "training_data_max_records"]
            }
        )

    # Service tier limits
    if "limits" in return_value:
        for tier, tier_limits in return_value["limits"].items():
            attributes.update(
                {
                    f"ibm.watsonx.model.limits.{tier}.{key}": value
                    for key, value in tier_limits.items()
                    if key in ["call_time", "max_output_tokens"]
                }
            )

    # Model lifecycle
    if "lifecycle" in return_value:
        attributes.update(
            {
                f"ibm.watsonx.model.lifecycle.{stage['id']}": stage["start_date"]
                for stage in return_value["lifecycle"]
                if "id" in stage and "start_date" in stage
            }
        )

    # Training parameters
    if "training_parameters" in return_value:
        attributes.update(
            {
                f"ibm.watsonx.model.training.{key}": str(value) if isinstance(value, dict) else value
                for key, value in return_value["training_parameters"].items()
            }
        )

    return attributes


def get_chat_attributes(
    args: Optional[Tuple] = None, kwargs: Optional[Dict] = None, return_value: Optional[Any] = None
) -> AttributeMap:
    """Extract attributes from chat method calls."""
    attributes = {}

    # Extract messages using helper function
    messages = extract_messages_from_args(args, kwargs)
    if messages:
        # Process each message in the conversation
        for i, message in enumerate(messages):
            if not isinstance(message, dict):
                continue

            # Extract role and content
            role = message.get("role", "")
            content = message.get("content", [])

            # Handle content which can be a list of different types (text, image_url)
            if isinstance(content, list):
                # Combine all text content
                text_content = []
                image_urls = []

                for content_item in content:
                    if isinstance(content_item, dict):
                        if content_item.get("type") == "text":
                            text_content.append(content_item.get("text", ""))
                        elif content_item.get("type") == "image_url":
                            image_url = content_item.get("image_url", {})
                            if isinstance(image_url, dict) and "url" in image_url:
                                url = image_url["url"]
                                # Only store URLs that start with http, otherwise use placeholder
                                if url and isinstance(url, str) and url.startswith(("http://", "https://")):
                                    image_urls.append(url)
                                else:
                                    image_urls.append("[IMAGE_PLACEHOLDER]")

                # Set text content if any
                if text_content:
                    attributes[MessageAttributes.PROMPT_CONTENT.format(i=i)] = " ".join(text_content)
                    attributes[MessageAttributes.PROMPT_TYPE.format(i=i)] = "text"
                    attributes[MessageAttributes.PROMPT_ROLE.format(i=i)] = role

                # Set image URLs if any
                if image_urls:
                    attributes[f"ibm.watsonx.chat.message.{i}.images"] = str(image_urls)
            else:
                # Handle string content
                attributes[MessageAttributes.PROMPT_CONTENT.format(i=i)] = str(content)
                attributes[MessageAttributes.PROMPT_TYPE.format(i=i)] = "text"
                attributes[MessageAttributes.PROMPT_ROLE.format(i=i)] = role

    # Extract parameters using helper functions
    params = extract_params_from_args(args, kwargs)
    if params:
        params_dict = convert_params_to_dict(params)
        if params_dict:
            attributes.update(extract_params_attributes(params_dict))

    # Extract response information
    if return_value and isinstance(return_value, dict):
        # Extract model information
        if "model_id" in return_value:
            attributes[SpanAttributes.LLM_REQUEST_MODEL] = return_value["model_id"]
        elif "model" in return_value:
            attributes[SpanAttributes.LLM_REQUEST_MODEL] = return_value["model"]

        # Extract completion from choices
        if "choices" in return_value:
            for idx, choice in enumerate(return_value["choices"]):
                if isinstance(choice, dict) and "message" in choice:
                    message = choice["message"]
                    if isinstance(message, dict):
                        if "content" in message:
                            attributes[MessageAttributes.COMPLETION_CONTENT.format(i=idx)] = message["content"]
                            attributes[MessageAttributes.COMPLETION_ROLE.format(i=idx)] = message.get(
                                "role", "assistant"
                            )
                            attributes[MessageAttributes.COMPLETION_TYPE.format(i=idx)] = "text"
                        if "finish_reason" in choice:
                            attributes[SpanAttributes.LLM_RESPONSE_STOP_REASON] = choice["finish_reason"]

        # Extract token usage
        if "usage" in return_value:
            usage = return_value["usage"]
            if isinstance(usage, dict):
                if "prompt_tokens" in usage:
                    attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = usage["prompt_tokens"]
                if "completion_tokens" in usage:
                    attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = usage["completion_tokens"]
                if "total_tokens" in usage:
                    attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = usage["total_tokens"]

        # Extract additional metadata
        if "id" in return_value:
            attributes["ibm.watsonx.chat.id"] = return_value["id"]
        if "model_version" in return_value:
            attributes["ibm.watsonx.model.version"] = return_value["model_version"]
        if "created_at" in return_value:
            attributes["ibm.watsonx.chat.created_at"] = return_value["created_at"]

    return attributes
