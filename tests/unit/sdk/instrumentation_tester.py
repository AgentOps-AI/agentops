from typing import Any, Dict, List, Protocol, Tuple, Union
import importlib
import unittest.mock as mock

from opentelemetry import trace as trace_api
from opentelemetry.sdk.trace import ReadableSpan, Span, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.util.types import Attributes

from agentops.sdk.core import tracer


def create_tracer_provider(
    **kwargs,
) -> Tuple[TracerProvider, InMemorySpanExporter, SimpleSpanProcessor]:
    """Helper to create a configured tracer provider.

    Creates and configures a `TracerProvider` with a
    `SimpleSpanProcessor` and a `InMemorySpanExporter`.
    All the parameters passed are forwarded to the TracerProvider
    constructor.

    Returns:
        A tuple with the tracer provider, memory exporter, and span processor.
    """
    tracer_provider = TracerProvider(**kwargs)
    memory_exporter = InMemorySpanExporter()

    # Use SimpleSpanProcessor instead of both processors to avoid duplication
    span_processor = SimpleSpanProcessor(memory_exporter)
    tracer_provider.add_span_processor(span_processor)

    return tracer_provider, memory_exporter, span_processor


def reset_trace_globals():
    """Reset the global trace state to avoid conflicts."""
    # Reset tracer provider
    trace_api._TRACER_PROVIDER = None

    # Reload the trace module to clear warning state
    importlib.reload(trace_api)


class HasAttributesViaProperty(Protocol):
    @property
    def attributes(self) -> Attributes: ...


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
    span_processor: SimpleSpanProcessor

    def __init__(self):
        """Initialize the instrumentation tester."""
        # Reset any global state first
        reset_trace_globals()

        # Shut down any existing tracing core
        # self._shutdown_core()

        # Create a new tracer provider and memory exporter
        (
            self.tracer_provider,
            self.memory_exporter,
            self.span_processor,
        ) = create_tracer_provider()

        # Set the tracer provider
        trace_api.set_tracer_provider(self.tracer_provider)

        # Create a mock for the meter provider
        self.mock_meter_provider = mock.MagicMock()

        # Patch the setup_telemetry function to return our test providers
        self.setup_telemetry_patcher = mock.patch(
            "agentops.sdk.core.setup_telemetry", return_value=(self.tracer_provider, self.mock_meter_provider)
        )
        self.mock_setup_telemetry = self.setup_telemetry_patcher.start()

        # Reset the tracing core to force reinitialization
        core = tracer
        core._initialized = False
        core._provider = None

        # Initialize the core, which will now use our mocked setup_telemetry
        core.initialize()

        self.clear_spans()

    def _shutdown_core(self):
        """Safely shut down the tracing core."""
        try:
            tracer.shutdown()
        except Exception as e:
            print(f"Warning: Error shutting down tracing core: {e}")

    def clear_spans(self):
        """Clear all spans from the memory exporter."""
        # Force flush spans
        self.span_processor.force_flush()

        # Then clear the memory
        self.memory_exporter.clear()
        print("Cleared all spans from memory exporter")

    def reset(self):
        """Reset the instrumentation tester."""
        # Force flush any pending spans
        self.span_processor.force_flush()

        # Clear any existing spans
        self.clear_spans()

        # Reset global trace state
        reset_trace_globals()

        # Set our tracer provider again
        trace_api.set_tracer_provider(self.tracer_provider)

        # Shut down and re-initialize the tracing core
        self._shutdown_core()

        # Reset the mock setup_telemetry function
        self.mock_setup_telemetry.reset_mock()

        # Reset the tracing core to force reinitialization
        core = tracer
        core._initialized = False
        core._provider = None

        # Initialize the core, which will now use our mocked setup_telemetry
        core.initialize()

    def __del__(self):
        """Clean up resources when the tester is garbage collected."""
        try:
            # Stop the patcher when the tester is deleted
            self.setup_telemetry_patcher.stop()
        except Exception:
            pass

    def get_finished_spans(self) -> List[ReadableSpan]:
        """Get all finished spans."""
        # Force flush any pending spans
        self.span_processor.force_flush()

        # Get the spans
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
            span for span in self.get_finished_spans() if span.attributes and span.attributes.get("span.kind") == kind
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
