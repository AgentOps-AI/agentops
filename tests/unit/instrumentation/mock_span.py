"""
Utility module for mocking spans and tracers in OpenTelemetry tests.
This provides reusable mock classes for testing instrumentation.
"""

import builtins
import json
from typing import Any, Dict, Optional


class MockSpanData:
    """Mock span data object for testing instrumentation."""
    
    def __init__(self, data: Any, span_type: str = "GenerationSpanData"):
        """Initialize mock span data.
        
        Args:
            data: The data dictionary to include in the span data
            span_type: The type of span data (used for __class__.__name__)
        """
        # Set all keys from the data dictionary as attributes
        for key, value in data.items():
            setattr(self, key, value)
            
        self.__class__.__name__ = span_type


class MockSpan:
    """Mock span object for testing instrumentation."""
    
    def __init__(self, data: Any, span_type: str = "GenerationSpanData"):
        """Initialize mock span.
        
        Args:
            data: The data dictionary to include in the span data
            span_type: The type of span data
        """
        self.trace_id = "trace123"
        self.span_id = "span456"
        self.parent_id = "parent789"
        self.span_data = MockSpanData(data, span_type)
        self.error = None


class MockTracingSpan:
    """Mock span for capturing attributes."""
    
    def __init__(self):
        """Initialize the mock span."""
        self.attributes = {}
        
    def set_attribute(self, key: str, value: Any) -> None:
        """Set an attribute on the span, capturing it for testing."""
        self.attributes[key] = value
    
    def set_status(self, status: Any) -> None:
        """Mock setting status."""
        pass
        
    def record_exception(self, exception: Exception, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Mock recording an exception."""
        pass
    
    def __enter__(self) -> 'MockTracingSpan':
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        pass


class MockTracer:
    """Mock tracer that captures attributes set on spans."""
    
    def __init__(self, captured_attributes: Dict[str, Any]):
        """Initialize the mock tracer.
        
        Args:
            captured_attributes: Dictionary to store captured attributes
        """
        self.captured_attributes = captured_attributes
    
    def start_as_current_span(self, name: str, kind: Any = None, attributes: Optional[Dict[str, Any]] = None):
        """Start a new span and capture attributes."""
        span = CapturedAttributeSpan(self.captured_attributes)
        # Set any provided attributes
        if attributes:
            for key, val in attributes.items():
                span.set_attribute(key, val)
        return span


class CapturedAttributeSpan(MockTracingSpan):
    """Mock span that captures attributes in a shared dictionary."""
    
    def __init__(self, captured_attributes: Dict[str, Any]):
        """Initialize with a shared dictionary for capturing attributes.
        
        Args:
            captured_attributes: Dictionary to store captured attributes
        """
        super().__init__()
        self.captured_attributes = captured_attributes
        
    def set_attribute(self, key: str, value: Any) -> None:
        """Set an attribute, capturing it in the shared dictionary."""
        self.captured_attributes[key] = value


def setup_mock_tracer(captured_attributes: Dict[str, Any]):
    """Set up a mock tracer by monkey patching OpenTelemetry.
    
    Args:
        captured_attributes: Dictionary to store captured attributes
        
    Returns:
        The original import function for cleanup
    """
    original_import = builtins.__import__
    
    def mocked_import(name, *args, **kwargs):
        module = original_import(name, *args, **kwargs)
        if name == 'opentelemetry.trace':
            # Monkey patch the get_tracer function
            module.get_tracer = lambda *args, **kwargs: MockTracer(captured_attributes)
        return module
    
    builtins.__import__ = mocked_import
    return original_import


def process_with_instrumentor(mock_span, exporter_class, captured_attributes: Dict[str, Any]):
    """Process a mock span with an instrumentor exporter.
    
    Args:
        mock_span: The mock span to process
        exporter_class: The exporter class to use
        captured_attributes: Dictionary to store captured attributes
        
    Returns:
        The captured attributes
    """
    # Create a direct instance of the exporter
    exporter = exporter_class()
    
    # Add core trace/span attributes from the mock_span directly to the captured_attributes
    # This ensures that both semantic convention attributes and direct access attributes work
    from agentops.semconv import CoreAttributes
    
    core_attribute_mapping = {
        CoreAttributes.TRACE_ID: "trace_id",   # "trace.id"
        CoreAttributes.SPAN_ID: "span_id",     # "span.id"
        CoreAttributes.PARENT_ID: "parent_id", # "parent.id"
    }
    
    for target_attr, source_attr in core_attribute_mapping.items():
        if hasattr(mock_span, source_attr):
            value = getattr(mock_span, source_attr)
            if value is not None:
                captured_attributes[target_attr] = value
    
    # Monkey patch the get_tracer function to return our MockTracer
    original_import = setup_mock_tracer(captured_attributes)
    
    # Call the exporter's export_span method (public API)
    try:
        exporter.export_span(mock_span)
    finally:
        # Restore the original import function
        builtins.__import__ = original_import
    
    return captured_attributes