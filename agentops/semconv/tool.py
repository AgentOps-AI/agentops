"""Attributes specific to tool spans."""


class ToolAttributes:
    """Attributes specific to tool spans."""

    # Identity
    TOOL_ID = "tool.id"  # Unique identifier for the tool
    TOOL_NAME = "tool.name"  # Name of the tool
    TOOL_DESCRIPTION = "tool.description"  # Description of the tool

    # Execution
    TOOL_PARAMETERS = "tool.parameters"  # Parameters passed to the tool
    TOOL_RESULT = "tool.result"  # Result returned by the tool
    TOOL_STATUS = "tool.status"  # Status of tool execution
