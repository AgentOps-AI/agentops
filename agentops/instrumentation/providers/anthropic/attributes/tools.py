"""Tool-related attribute extraction for Anthropic API."""

import json
from typing import Dict, Any, List, Optional

from agentops.logging import logger
from agentops.semconv import SpanAttributes, MessageAttributes, ToolAttributes, ToolStatus
from agentops.instrumentation.common.attributes import AttributeMap


def extract_tool_definitions(tools: List[Dict[str, Any]]) -> AttributeMap:
    """Extract attributes from tool definitions.

    Processes a list of Anthropic tool definitions and converts them into
    standardized attributes for OpenTelemetry instrumentation. This captures
    information about each tool's name, description, and input schema.

    Args:
        tools: List of tool definition objects

    Returns:
        Dictionary of tool-related attributes
    """
    attributes = {}

    try:
        if not tools:
            return attributes

        for i, tool in enumerate(tools):
            name = tool.get("name", "unknown")
            description = tool.get("description", "")

            attributes[MessageAttributes.TOOL_CALL_NAME.format(i=i)] = name
            attributes[MessageAttributes.TOOL_CALL_TYPE.format(i=i)] = "function"

            if description:
                attributes[MessageAttributes.TOOL_CALL_DESCRIPTION.format(i=i)] = description

            if "input_schema" in tool:
                attributes[MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=i)] = json.dumps(tool["input_schema"])

            tool_id = tool.get("id", f"tool-{i}")
            attributes[MessageAttributes.TOOL_CALL_ID.format(i=i)] = tool_id
            attributes[MessageAttributes.TOOL_CALL_NAME.format(i=i)] = name
            if description:
                attributes[MessageAttributes.TOOL_CALL_DESCRIPTION.format(i=i)] = description

        tool_names = [tool.get("name", "unknown") for tool in tools]
        attributes[SpanAttributes.LLM_REQUEST_FUNCTIONS] = json.dumps(tool_names)

        tool_schemas = []
        for tool in tools:
            schema = {"name": tool.get("name", "unknown"), "schema": {}}

            if "description" in tool:
                schema["schema"]["description"] = tool["description"]
            if "input_schema" in tool:
                schema["schema"]["input_schema"] = tool["input_schema"]

            tool_schemas.append(schema)

        attributes["anthropic.tools.schemas"] = json.dumps(tool_schemas)

    except Exception as e:
        logger.debug(f"[agentops.instrumentation.anthropic] Error extracting tool definitions: {e}")

    return attributes


def extract_tool_use_blocks(content_blocks: List[Any]) -> Optional[List[Dict[str, Any]]]:
    """Extract tool use blocks from message content.

    Analyzes message content blocks to find and extract tool use information.
    This is used to track which tools the model called and with what parameters.

    Args:
        content_blocks: List of content blocks from a Message

    Returns:
        List of tool use information or None if no tools used
    """
    if not content_blocks:
        return None

    try:
        tool_uses = []

        for block in content_blocks:
            if hasattr(block, "type") and block.type == "tool_use":
                tool_use = {
                    "name": block.name if hasattr(block, "name") else "unknown",
                    "id": block.id if hasattr(block, "id") else "unknown",
                }

                if hasattr(block, "input"):
                    try:
                        if isinstance(block.input, dict):
                            tool_use["input"] = block.input
                        elif isinstance(block.input, str):
                            tool_use["input"] = json.loads(block.input)
                        else:
                            tool_use["input"] = {"raw": str(block.input)}
                    except Exception:
                        tool_use["input"] = {"raw": str(block.input)}

                tool_uses.append(tool_use)

        return tool_uses if tool_uses else None

    except Exception as e:
        logger.debug(f"[agentops.instrumentation.anthropic] Error extracting tool use blocks: {e}")
        return None


def extract_tool_results(content_blocks: List[Any]) -> Optional[List[Dict[str, Any]]]:
    """Extract tool result blocks from message content.

    Analyzes message content blocks to find and extract tool result information.
    This is used to track the outputs returned from tool executions.

    Args:
        content_blocks: List of content blocks from a Message

    Returns:
        List of tool result information or None if no tool results
    """
    if not content_blocks:
        return None

    try:
        tool_results = []

        for block in content_blocks:
            if hasattr(block, "type") and block.type == "tool_result":
                tool_result = {
                    "tool_use_id": block.tool_use_id if hasattr(block, "tool_use_id") else "unknown",
                }

                if hasattr(block, "content"):
                    try:
                        if isinstance(block.content, dict):
                            tool_result["content"] = block.content
                        elif isinstance(block.content, str):
                            tool_result["content"] = json.loads(block.content)
                        else:
                            tool_result["content"] = {"raw": str(block.content)}
                    except Exception:
                        tool_result["content"] = {"raw": str(block.content)}

                tool_results.append(tool_result)

        return tool_results if tool_results else None

    except Exception as e:
        logger.debug(f"[agentops.instrumentation.anthropic] Error extracting tool results: {e}")
        return None


def get_tool_attributes(message_content: List[Any]) -> AttributeMap:
    """Extract tool-related attributes from message content.

    Processes message content to extract comprehensive information about
    tool usage, including both tool calls and tool results. This creates a
    standardized set of attributes representing the tool interaction flow.

    Args:
        message_content: List of content blocks from a Message

    Returns:
        Dictionary of tool-related attributes
    """
    attributes = {}

    try:
        tool_uses = extract_tool_use_blocks(message_content)
        if tool_uses:
            for j, tool_use in enumerate(tool_uses):
                tool_name = tool_use.get("name", "unknown")
                tool_id = tool_use.get("id", f"tool-call-{j}")

                attributes[MessageAttributes.COMPLETION_TOOL_CALL_ID.format(i=0, j=j)] = tool_id
                attributes[MessageAttributes.COMPLETION_TOOL_CALL_NAME.format(i=0, j=j)] = tool_name
                attributes[MessageAttributes.COMPLETION_TOOL_CALL_TYPE.format(i=0, j=j)] = "function"

                tool_input = tool_use.get("input", {})
                if isinstance(tool_input, dict):
                    input_str = json.dumps(tool_input)
                else:
                    input_str = str(tool_input)
                attributes[MessageAttributes.COMPLETION_TOOL_CALL_ARGUMENTS.format(i=0, j=j)] = input_str

                attributes[MessageAttributes.TOOL_CALL_ID.format(i=j)] = tool_id
                attributes[MessageAttributes.TOOL_CALL_NAME.format(i=j)] = tool_name
                attributes[MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=j)] = input_str
                attributes[f"{ToolAttributes.TOOL_STATUS}.{j}"] = ToolStatus.EXECUTING.value

            attributes["anthropic.tool_calls.count"] = len(tool_uses)

        tool_results = extract_tool_results(message_content)
        if tool_results:
            attributes["anthropic.tool_results"] = json.dumps(tool_results)
            attributes["anthropic.tool_results.count"] = len(tool_results)

            for j, tool_result in enumerate(tool_results):
                tool_use_id = tool_result.get("tool_use_id", "unknown")

                tool_index = None
                for k in range(attributes.get("anthropic.tool_calls.count", 0)):
                    if attributes.get(MessageAttributes.COMPLETION_TOOL_CALL_ID.format(i=0, j=k)) == tool_use_id:
                        tool_index = k
                        break

                if tool_index is not None:
                    attributes[MessageAttributes.COMPLETION_TOOL_CALL_STATUS.format(i=0, j=tool_index)] = "complete"

                    content = tool_result.get("content", {})
                    if isinstance(content, dict):
                        content_str = json.dumps(content)
                    else:
                        content_str = str(content)

                    attributes[f"{ToolAttributes.TOOL_STATUS}.{tool_index}"] = ToolStatus.SUCCEEDED.value
                    attributes[f"{ToolAttributes.TOOL_RESULT}.{tool_index}"] = content_str

                    attributes[f"anthropic.tool_result.{tool_index}.content"] = content_str

    except Exception as e:
        logger.debug(f"[agentops.instrumentation.anthropic] Error extracting tool attributes: {e}")

    return attributes
