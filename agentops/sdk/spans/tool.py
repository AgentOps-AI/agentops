from __future__ import annotations

from typing import Any, Dict, Optional, Union

from opentelemetry.trace import Span, StatusCode

from agentops.sdk.traced import TracedObject
from agentops.logging import logger
from agentops.semconv.tool import ToolAttributes
from agentops.semconv.span_kinds import SpanKind


class ToolSpan(TracedObject):
    """
    Represents a tool span, which tracks tool operations.
    
    Tool spans are typically short-lived operations that perform a specific task
    and return a result.
    """
    
    def __init__(
        self,
        name: str,
        tool_type: str,
        parent: Optional[Union[TracedObject, Span]] = None,
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
        kwargs.setdefault("kind", SpanKind.TOOL)
        
        # Initialize base class
        super().__init__(name=name, parent=parent, **kwargs)
        
        # Store tool-specific attributes
        self._tool_type = tool_type
        self._input = None
        self._output = None
        
        # Set attributes
        self._attributes.update({
            ToolAttributes.TOOL_NAME: name,
            ToolAttributes.TOOL_DESCRIPTION: tool_type,
        })
        
        logger.debug(f"ToolSpan initialized: name={name}, tool_type={tool_type}")
    
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
        
        self.set_attribute(ToolAttributes.TOOL_PARAMETERS, input_str)
        
        # Log a truncated version of the input to avoid huge log lines
        if isinstance(input_str, str):
            log_input = input_str[:100] + "..." if len(input_str) > 100 else input_str
        else:
            log_input = str(input_str)
        logger.debug(f"ToolSpan input set: {self.name}, input={log_input}")
    
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
        
        self.set_attribute(ToolAttributes.TOOL_RESULT, output_str)
        
        # Log a truncated version of the output to avoid huge log lines
        if isinstance(output_str, str):
            log_output = output_str[:100] + "..." if len(output_str) > 100 else output_str
        else:
            log_output = str(output_str)
        logger.debug(f"ToolSpan output set: {self.name}, output={log_output}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = super().to_dict()
        result.update({
            "tool_type": self._tool_type,
            "input": self._input,
            "output": self._output,
        })
        logger.debug(f"ToolSpan converted to dict: {self.name}, tool_type={self._tool_type}")
        return result 