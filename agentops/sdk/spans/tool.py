from __future__ import annotations

from typing import Any, Dict, Optional, Union

from opentelemetry.trace import Span, StatusCode

from agentops.sdk.spanned import SpannedBase


class ToolSpan(SpannedBase):
    """
    Represents a tool span, which tracks tool operations.
    
    Tool spans are typically short-lived operations that perform a specific task
    and return a result.
    """
    
    def __init__(
        self,
        name: str,
        tool_type: str,
        parent: Optional[Union[SpannedBase, Span]] = None,
        **kwargs
    ):
        """
        Initialize a tool span.
        
        Args:
            name: Name of the tool
            tool_type: Type of tool (e.g., "search", "calculator", "database")
            parent: Optional parent span or spanned object
            **kwargs: Additional keyword arguments
        """
        # Set default values
        kwargs.setdefault("kind", "tool")
        
        # Initialize base class
        super().__init__(name=name, kind="tool", parent=parent, **kwargs)
        
        # Store tool-specific attributes
        self._tool_type = tool_type
        self._input = None
        self._output = None
        
        # Set attributes
        self._attributes.update({
            "tool.name": name,
            "tool.type": tool_type,
        })
    
    def set_input(self, input_data: Any) -> None:
        """
        Set the tool input.
        
        Args:
            input_data: Input data for the tool
        """
        self._input = input_data
        
        # Convert input to string if it's not a basic type
        if not isinstance(input_data, (str, int, float, bool)):
            input_str = str(input_data)
        else:
            input_str = input_data
        
        self.set_attribute("tool.input", input_str)
    
    def set_output(self, output_data: Any) -> None:
        """
        Set the tool output.
        
        Args:
            output_data: Output data from the tool
        """
        self._output = output_data
        
        # Convert output to string if it's not a basic type
        if not isinstance(output_data, (str, int, float, bool)):
            output_str = str(output_data)
        else:
            output_str = output_data
        
        self.set_attribute("tool.output", output_str)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = super().to_dict()
        result.update({
            "tool_type": self._tool_type,
            "input": self._input,
            "output": self._output,
        })
        return result 