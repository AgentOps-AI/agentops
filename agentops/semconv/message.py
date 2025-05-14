"""Semantic conventions for message-related attributes in AI systems."""


class MessageAttributes:
    """Semantic conventions for message-related attributes in AI systems."""

    PROMPT_ROLE = "gen_ai.prompt.{i}.role"  # Role of the prompt message
    PROMPT_CONTENT = "gen_ai.prompt.{i}.content"  # Content of the prompt message
    PROMPT_TYPE = "gen_ai.prompt.{i}.type"  # Type of the prompt message
    PROMPT_SPEAKER = "gen_ai.prompt.{i}.speaker"  # Speaker/agent name for the prompt message

    # Indexed function calls (with {i} for interpolation)
    TOOL_CALL_ID = "gen_ai.request.tools.{i}.id"  # Unique identifier for the function call at index {i}
    TOOL_CALL_TYPE = "gen_ai.request.tools.{i}.type"  # Type of the function call at index {i}
    TOOL_CALL_NAME = "gen_ai.request.tools.{i}.name"  # Name of the function call at index {i}
    TOOL_CALL_DESCRIPTION = "gen_ai.request.tools.{i}.description"  # Description of the function call at index {i}
    TOOL_CALL_ARGUMENTS = "gen_ai.request.tools.{i}.arguments"  # Arguments for function call at index {i}

    # Indexed completions (with {i} for interpolation)
    COMPLETION_ID = "gen_ai.completion.{i}.id"  # Unique identifier for the completion
    COMPLETION_TYPE = "gen_ai.completion.{i}.type"  # Type of the completion at index {i}
    COMPLETION_ROLE = "gen_ai.completion.{i}.role"  # Role of the completion message at index {i}
    COMPLETION_CONTENT = "gen_ai.completion.{i}.content"  # Content of the completion message at index {i}
    COMPLETION_FINISH_REASON = "gen_ai.completion.{i}.finish_reason"  # Finish reason for completion at index {i}
    COMPLETION_SPEAKER = "gen_ai.completion.{i}.speaker"  # Speaker/agent name for the completion message

    # Indexed tool calls (with {i}/{j} for nested interpolation)
    COMPLETION_TOOL_CALL_ID = "gen_ai.completion.{i}.tool_calls.{j}.id"  # ID of tool call {j} in completion {i}
    COMPLETION_TOOL_CALL_TYPE = "gen_ai.completion.{i}.tool_calls.{j}.type"  # Type of tool call {j} in completion {i}
    COMPLETION_TOOL_CALL_STATUS = (
        "gen_ai.completion.{i}.tool_calls.{j}.status"  # Status of tool call {j} in completion {i}
    )
    COMPLETION_TOOL_CALL_NAME = (
        "gen_ai.completion.{i}.tool_calls.{j}.name"  # Name of the tool called in tool call {j} in completion {i}
    )
    COMPLETION_TOOL_CALL_DESCRIPTION = (
        "gen_ai.completion.{i}.tool_calls.{j}.description"  # Description of the tool call {j} in completion {i}
    )
    COMPLETION_TOOL_CALL_STATUS = (
        "gen_ai.completion.{i}.tool_calls.{j}.status"  # Status of the tool call {j} in completion {i}
    )
    COMPLETION_TOOL_CALL_ARGUMENTS = (
        "gen_ai.completion.{i}.tool_calls.{j}.arguments"  # Arguments for tool call {j} in completion {i}
    )

    # Indexed annotations of the internal tools (with {i}/{j} for nested interpolation)
    COMPLETION_ANNOTATION_START_INDEX = (
        "gen_ai.completion.{i}.annotations.{j}.start_index"  # Start index of the URL annotation {j} in completion {i}
    )
    COMPLETION_ANNOTATION_END_INDEX = (
        "gen_ai.completion.{i}.annotations.{j}.end_index"  # End index of the URL annotation {j} in completion {i}
    )
    COMPLETION_ANNOTATION_TITLE = (
        "gen_ai.completion.{i}.annotations.{j}.title"  # Title of the URL annotation {j} in completion {i}
    )
    COMPLETION_ANNOTATION_TYPE = (
        "gen_ai.completion.{i}.annotations.{j}.type"  # Type of the URL annotation {j} in completion {i}
    )
    COMPLETION_ANNOTATION_URL = (
        "gen_ai.completion.{i}.annotations.{j}.url"  # URL link of the URL annotation {j} in completion {i}
    )
