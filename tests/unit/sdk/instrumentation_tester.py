from typing import Any, Dict, List, Optional, Protocol, Tuple, Union

from opentelemetry import trace as trace_api
from opentelemetry.sdk.trace import ReadableSpan, Span, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.util.types import Attributes

import agentops
from agentops.sdk.core import TracingCore


def create_tracer_provider(**kwargs) -> Tuple[TracerProvider, InMemorySpanExporter]:
    """Helper to create a configured tracer provider.

    Creates and configures a `TracerProvider` with a
    `SimpleSpanProcessor` and a `InMemorySpanExporter`.
    All the parameters passed are forwarded to the TracerProvider
    constructor.

    Returns:
        A tuple with the tracer provider in the first element and the
        in-memory span exporter in the second.
    """
    tracer_provider = TracerProvider(**kwargs)
    memory_exporter = InMemorySpanExporter()
    span_processor = SimpleSpanProcessor(memory_exporter)
    tracer_provider.add_span_processor(span_processor)

    return tracer_provider, memory_exporter


class HasAttributesViaProperty(Protocol):
    @property
    def attributes(self) -> Attributes:
        ...


class HasAttributesViaAttr(Protocol):
    attributes: Attributes


HasAttributes = Union[HasAttributesViaProperty, HasAttributesViaAttr]


class InstrumentationTester:
    """
    A utility class for testing instrumentation in the AgentOps SDK.
    
    This class provides methods for setting up a test environment with
    in-memory span exporters, and for asserting properties of spans.
    """
    
    tracer_provider: TracerProvider
    memory_exporter: InMemorySpanExporter

    def __init__(self):
        """Initialize the instrumentation tester."""
        # Create a new tracer provider and memory exporter
        self.tracer_provider, self.memory_exporter = create_tracer_provider()
        
        # Reset the global tracer provider and set the new one
        trace_api._TRACER_PROVIDER = None
        trace_api.set_tracer_provider(self.tracer_provider)
        
        # Create a span processor for immediate export
        self.span_processor = SimpleSpanProcessor(self.memory_exporter)
        self.tracer_provider.add_span_processor(self.span_processor)
        
        # Shut down any existing tracing core
        TracingCore.get_instance().shutdown()
        
        # Get a fresh instance of the tracing core
        core = TracingCore.get_instance()
        
        # Set the tracing core's provider to our provider
        core._provider = self.tracer_provider
        core._initialized = True
        
        # Reset the factory
        from agentops.sdk.factory import SpanFactory
        SpanFactory._span_types = {}
        SpanFactory._initialized = False
        
        # Auto-register span types
        SpanFactory.auto_register_span_types()
        
        # Clear any existing spans
        self.clear_spans()

    def clear_spans(self):
        """Clear all spans from the memory exporter."""
        self.memory_exporter.clear()
        print("Cleared all spans from memory exporter")

    def reset(self):
        """Reset the instrumentation tester."""
        # Clear any existing spans
        self.clear_spans()
        
        # Reset the global tracer provider
        if trace_api._TRACER_PROVIDER != self.tracer_provider:
            trace_api._TRACER_PROVIDER = None
            trace_api.set_tracer_provider(self.tracer_provider)
        
        # Shut down any existing tracing core
        TracingCore.get_instance().shutdown()
        
        # Get a fresh instance of the tracing core
        core = TracingCore.get_instance()
        
        # Set the tracing core's provider to our provider
        core._provider = self.tracer_provider
        core._initialized = True
        
        # Reset the factory
        from agentops.sdk.factory import SpanFactory
        SpanFactory._span_types = {}
        SpanFactory._initialized = False
        
        # Auto-register span types
        SpanFactory.auto_register_span_types()

    def get_finished_spans(self) -> List[ReadableSpan]:
        """Get all finished spans."""
        spans = list(self.memory_exporter.get_finished_spans())
        print(f"Instrumentation Tester: Found {len(spans)} finished spans")
        for i, span in enumerate(spans):
            print(f"Span {i}: name={span.name}, attributes={span.attributes}")
        return spans
    
    def get_spans_by_name(self, name: str) -> List[ReadableSpan]:
        """Get all spans with the given name."""
        return [span for span in self.get_finished_spans() if span.name == name]
    
    def get_spans_by_kind(self, kind: str) -> List[ReadableSpan]:
        """Get all spans with the given kind."""
        return [
            span for span in self.get_finished_spans() 
            if span.attributes and span.attributes.get("span.kind") == kind
        ]

    @staticmethod
    def assert_has_attributes(obj: HasAttributes, attributes: Dict[str, Any]):
        """Assert that an object has the given attributes."""
        import json
        
        assert obj.attributes is not None
        for key, val in attributes.items():
            assert key in obj.attributes, f"Key {key!r} not found in attributes"
            
            actual_val = obj.attributes[key]
            
            # Try to handle JSON-serialized values
            if isinstance(actual_val, str) and isinstance(val, (list, dict)):
                try:
                    actual_val = json.loads(actual_val)
                except json.JSONDecodeError:
                    pass
            
            assert actual_val == val, f"Value for key {key!r} does not match: {actual_val} != {val}"

    @staticmethod
    def assert_span_instrumented_for(span: Union[Span, ReadableSpan], module):
        """Assert that a span is instrumented for the given module."""
        assert span.instrumentation_scope is not None
        assert span.instrumentation_scope.name == module.__name__
        assert span.instrumentation_scope.version == module.__version__ 