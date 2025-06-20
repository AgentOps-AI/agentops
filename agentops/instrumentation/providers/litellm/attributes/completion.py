"""Completion-specific attribute extraction for LiteLLM instrumentation.

This module provides functions to extract attributes specific to
completion operations (chat completions, text completions, etc.).
"""

from typing import Any, Dict, List, Optional

from agentops.instrumentation.providers.litellm.utils import (
    estimate_tokens,
    safe_get_attribute,
)


def extract_completion_request_attributes(
    messages: Optional[List[Dict[str, Any]]], kwargs: Dict[str, Any]
) -> Dict[str, Any]:
    """Extract attributes from completion request parameters.

    Args:
        messages: List of message dictionaries (for chat completions)
        kwargs: Additional keyword arguments

    Returns:
        Dictionary of completion request attributes
    """
    attributes = {}

    # Message analysis
    if messages:
        attributes["llm.request.messages_count"] = len(messages)

        # Analyze message roles
        role_counts = {}
        total_content_length = 0
        has_images = False
        has_function_calls = False
        has_tool_calls = False

        for msg in messages:
            # Count roles
            role = msg.get("role", "unknown")
            role_counts[role] = role_counts.get(role, 0) + 1

            # Analyze content
            content = msg.get("content")
            if content:
                if isinstance(content, str):
                    total_content_length += len(content)
                elif isinstance(content, list):
                    # Multi-modal content
                    for item in content:
                        if isinstance(item, dict):
                            if item.get("type") == "text" and "text" in item:
                                total_content_length += len(item["text"])
                            elif item.get("type") == "image_url":
                                has_images = True

            # Check for function/tool calls
            if "function_call" in msg:
                has_function_calls = True
            if "tool_calls" in msg:
                has_tool_calls = True

        # Set role counts
        for role, count in role_counts.items():
            attributes[f"llm.request.messages.{role}_count"] = count

        attributes["llm.request.total_content_length"] = total_content_length
        attributes["llm.request.estimated_prompt_tokens"] = estimate_tokens(str(messages))

        if has_images:
            attributes["llm.request.has_images"] = True
        if has_function_calls:
            attributes["llm.request.has_function_calls"] = True
        if has_tool_calls:
            attributes["llm.request.has_tool_calls"] = True

    # Prompt (for non-chat completions)
    elif "prompt" in kwargs:
        prompt = kwargs["prompt"]
        if isinstance(prompt, str):
            attributes["llm.request.prompt_length"] = len(prompt)
            attributes["llm.request.estimated_prompt_tokens"] = estimate_tokens(prompt)
        elif isinstance(prompt, list):
            attributes["llm.request.prompt_count"] = len(prompt)
            total_length = sum(len(p) if isinstance(p, str) else 0 for p in prompt)
            attributes["llm.request.prompt_total_length"] = total_length

    # Model parameters
    model_params = [
        "temperature",
        "max_tokens",
        "top_p",
        "frequency_penalty",
        "presence_penalty",
        "stop",
        "n",
        "logprobs",
        "echo",
        "best_of",
        "logit_bias",
        "suffix",
        "seed",
    ]

    for param in model_params:
        if param in kwargs and kwargs[param] is not None:
            attributes[f"llm.request.{param}"] = kwargs[param]

    # Streaming
    if "stream" in kwargs:
        attributes["llm.request.stream"] = bool(kwargs["stream"])

    # Response format
    if "response_format" in kwargs:
        format_info = kwargs["response_format"]
        if isinstance(format_info, dict):
            if "type" in format_info:
                attributes["llm.request.response_format"] = format_info["type"]
        else:
            attributes["llm.request.response_format"] = str(format_info)

    # Function calling
    if "functions" in kwargs:
        functions = kwargs["functions"]
        attributes["llm.request.functions_count"] = len(functions) if isinstance(functions, list) else 1

        # Extract function names
        if isinstance(functions, list):
            func_names = [f.get("name", "unknown") for f in functions if isinstance(f, dict)]
            if func_names:
                attributes["llm.request.function_names"] = ",".join(func_names[:10])  # Limit to 10

    if "function_call" in kwargs:
        func_call = kwargs["function_call"]
        if isinstance(func_call, dict) and "name" in func_call:
            attributes["llm.request.function_call_name"] = func_call["name"]
        else:
            attributes["llm.request.function_call_mode"] = str(func_call)

    # Tool calling
    if "tools" in kwargs:
        tools = kwargs["tools"]
        attributes["llm.request.tools_count"] = len(tools) if isinstance(tools, list) else 1

        # Extract tool types and names
        if isinstance(tools, list):
            tool_types = {}
            tool_names = []

            for tool in tools:
                if isinstance(tool, dict):
                    tool_type = tool.get("type", "unknown")
                    tool_types[tool_type] = tool_types.get(tool_type, 0) + 1

                    if tool_type == "function" and "function" in tool:
                        func_name = tool["function"].get("name")
                        if func_name:
                            tool_names.append(func_name)

            for tool_type, count in tool_types.items():
                attributes[f"llm.request.tools.{tool_type}_count"] = count

            if tool_names:
                attributes["llm.request.tool_names"] = ",".join(tool_names[:10])  # Limit to 10

    if "tool_choice" in kwargs:
        tool_choice = kwargs["tool_choice"]
        if isinstance(tool_choice, dict) and "function" in tool_choice:
            attributes["llm.request.tool_choice_function"] = tool_choice["function"].get("name", "unknown")
        else:
            attributes["llm.request.tool_choice_mode"] = str(tool_choice)

    return attributes


def extract_completion_response_attributes(response: Any) -> Dict[str, Any]:
    """Extract attributes from completion response.

    Args:
        response: Response object from LiteLLM

    Returns:
        Dictionary of completion response attributes
    """
    attributes = {}

    # Choices
    choices = safe_get_attribute(response, "choices")
    if choices and isinstance(choices, list):
        attributes["llm.response.choices_count"] = len(choices)

        # Analyze first choice (most common case)
        if choices:
            first_choice = choices[0]

            # Finish reason
            finish_reason = safe_get_attribute(first_choice, "finish_reason")
            if finish_reason:
                attributes["llm.response.finish_reason"] = finish_reason

            # Index
            index = safe_get_attribute(first_choice, "index")
            if index is not None:
                attributes["llm.response.first_choice_index"] = index

            # Message content
            message = safe_get_attribute(first_choice, "message")
            if message:
                # Content
                content = safe_get_attribute(message, "content")
                if content:
                    attributes["llm.response.content_length"] = len(content)
                    attributes["llm.response.estimated_completion_tokens"] = estimate_tokens(content)

                # Role
                role = safe_get_attribute(message, "role")
                if role:
                    attributes["llm.response.message_role"] = role

                # Function call
                function_call = safe_get_attribute(message, "function_call")
                if function_call:
                    attributes["llm.response.has_function_call"] = True

                    func_name = safe_get_attribute(function_call, "name")
                    if func_name:
                        attributes["llm.response.function_call_name"] = func_name

                    func_args = safe_get_attribute(function_call, "arguments")
                    if func_args:
                        attributes["llm.response.function_call_arguments_length"] = len(func_args)

                # Tool calls
                tool_calls = safe_get_attribute(message, "tool_calls")
                if tool_calls and isinstance(tool_calls, list):
                    attributes["llm.response.tool_calls_count"] = len(tool_calls)

                    # Analyze tool calls
                    tool_types = {}
                    tool_names = []

                    for tool_call in tool_calls:
                        tool_type = safe_get_attribute(tool_call, "type")
                        if tool_type:
                            tool_types[tool_type] = tool_types.get(tool_type, 0) + 1

                        if tool_type == "function":
                            function = safe_get_attribute(tool_call, "function")
                            if function:
                                func_name = safe_get_attribute(function, "name")
                                if func_name:
                                    tool_names.append(func_name)

                    for t_type, count in tool_types.items():
                        attributes[f"llm.response.tool_calls.{t_type}_count"] = count

                    if tool_names:
                        attributes["llm.response.tool_call_names"] = ",".join(tool_names)

            # Text (for non-chat completions)
            text = safe_get_attribute(first_choice, "text")
            if text:
                attributes["llm.response.text_length"] = len(text)
                attributes["llm.response.estimated_completion_tokens"] = estimate_tokens(text)

            # Logprobs
            logprobs = safe_get_attribute(first_choice, "logprobs")
            if logprobs:
                attributes["llm.response.has_logprobs"] = True

                # Token logprobs
                token_logprobs = safe_get_attribute(logprobs, "token_logprobs")
                if token_logprobs and isinstance(token_logprobs, list):
                    attributes["llm.response.logprobs_count"] = len(token_logprobs)

        # Check if all choices have the same finish reason
        if len(choices) > 1:
            finish_reasons = set()
            for choice in choices:
                reason = safe_get_attribute(choice, "finish_reason")
                if reason:
                    finish_reasons.add(reason)

            if len(finish_reasons) == 1:
                attributes["llm.response.all_same_finish_reason"] = True
            else:
                attributes["llm.response.unique_finish_reasons"] = len(finish_reasons)

    return attributes


def extract_function_calling_attributes(request_kwargs: Dict[str, Any], response: Any) -> Dict[str, Any]:
    """Extract detailed function calling attributes.

    Args:
        request_kwargs: Request keyword arguments
        response: Response object from LiteLLM

    Returns:
        Dictionary of function calling attributes
    """
    attributes = {}

    # Request-side function definitions
    if "functions" in request_kwargs:
        functions = request_kwargs["functions"]
        if isinstance(functions, list):
            # Analyze function complexity
            total_params = 0
            required_params = 0

            for func in functions:
                if isinstance(func, dict) and "parameters" in func:
                    params = func["parameters"]
                    if isinstance(params, dict):
                        properties = params.get("properties", {})
                        required = params.get("required", [])

                        total_params += len(properties)
                        required_params += len(required)

            if total_params > 0:
                attributes["llm.request.functions.total_parameters"] = total_params
                attributes["llm.request.functions.required_parameters"] = required_params
                attributes["llm.request.functions.avg_parameters_per_function"] = round(
                    total_params / len(functions), 2
                )

    # Response-side function calls
    choices = safe_get_attribute(response, "choices")
    if choices and isinstance(choices, list):
        total_function_calls = 0

        for choice in choices:
            message = safe_get_attribute(choice, "message")
            if message:
                # Single function call
                if safe_get_attribute(message, "function_call"):
                    total_function_calls += 1

                # Multiple tool calls
                tool_calls = safe_get_attribute(message, "tool_calls")
                if tool_calls and isinstance(tool_calls, list):
                    function_tool_calls = sum(1 for tc in tool_calls if safe_get_attribute(tc, "type") == "function")
                    total_function_calls += function_tool_calls

        if total_function_calls > 0:
            attributes["llm.response.total_function_calls"] = total_function_calls

    return attributes


def extract_moderation_attributes(messages: Optional[List[Dict[str, Any]]], response: Any) -> Dict[str, Any]:
    """Extract content moderation attributes if available.

    Args:
        messages: Request messages
        response: Response object

    Returns:
        Dictionary of moderation attributes
    """
    attributes = {}

    # Some providers include moderation scores in response
    moderation = safe_get_attribute(response, "moderation")
    if moderation:
        attributes["llm.response.has_moderation"] = True

        # Extract moderation details if available
        if isinstance(moderation, dict):
            for category, score in moderation.items():
                if isinstance(score, (int, float)):
                    attributes[f"llm.moderation.{category}"] = score

    # Check for content filtering in response
    choices = safe_get_attribute(response, "choices")
    if choices and isinstance(choices, list):
        filtered_count = 0

        for choice in choices:
            finish_reason = safe_get_attribute(choice, "finish_reason")
            if finish_reason and "content_filter" in str(finish_reason).lower():
                filtered_count += 1

        if filtered_count > 0:
            attributes["llm.response.content_filtered_count"] = filtered_count

    return attributes
