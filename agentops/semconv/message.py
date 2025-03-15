"""Semantic conventions for message-related attributes in AI systems."""


class MessageAttributes:
    """Semantic conventions for message-related attributes in AI systems."""

    # Message identity and metadata (following gen_ai prefix pattern)
    # DO NOT USE THESE we map responses types to use the completion conventions for now
    # MESSAGE_ROLE = "gen_ai.message.role"  # Role of the message (system, user, assistant, tool, function)
    # MESSAGE_CONTENT = "gen_ai.message.content"  # Content of the message
    
    # Indexed completions (with {i} for interpolation)
    COMPLETION_ROLE = "gen_ai.completion.{i}.role"  # Role of the completion message at index {i}
    COMPLETION_CONTENT = "gen_ai.completion.{i}.content"  # Content of the completion message at index {i}
    COMPLETION_FINISH_REASON = "gen_ai.completion.{i}.finish_reason"  # Finish reason for completion at index {i}
    
    # Indexed function calls (with {i} for interpolation)
    FUNCTION_CALL_NAME = "gen_ai.completion.{i}.function_call.name"  # Name of the function call at index {i}
    FUNCTION_CALL_ARGUMENTS = "gen_ai.completion.{i}.function_call.arguments"  # Arguments for function call at index {i}
    
    # Indexed tool calls (with {i}/{j} for nested interpolation)
    TOOL_CALL_ID = "gen_ai.completion.{i}.tool_calls.{j}.id"  # ID of tool call {j} in completion {i}
    TOOL_CALL_NAME = "gen_ai.completion.{i}.tool_calls.{j}.name"  # Name of the tool called in tool call {j} in completion {i}
    TOOL_CALL_ARGUMENTS = "gen_ai.completion.{i}.tool_calls.{j}.arguments"  # Arguments for tool call {j} in completion {i}