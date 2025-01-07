import pytest
from opentelemetry import trace as trace_api
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from agentops.event import ActionEvent, ErrorEvent, LLMEvent, ToolEvent


class InstrumentationTester:
    """Helper class for testing OTEL instrumentation"""
    def __init__(self):
        self.tracer_provider = TracerProvider()
        self.memory_exporter = InMemorySpanExporter()
        span_processor = SimpleSpanProcessor(self.memory_exporter)
        self.tracer_provider.add_span_processor(span_processor)
        
        # Reset and set global tracer provider
        trace_api.set_tracer_provider(self.tracer_provider)
        self.memory_exporter.clear()

    def get_finished_spans(self):
        return self.memory_exporter.get_finished_spans()

    def clear(self):
        """Clear captured spans"""
        self.memory_exporter.clear()


@pytest.fixture
def instrumentation():
    """Fixture providing instrumentation testing utilities"""
    return InstrumentationTester()


@pytest.fixture
def mock_llm_event():
    """Creates an LLMEvent for testing"""
    return LLMEvent(
        prompt="What is the meaning of life?",
        completion="42",
        model="gpt-4",
        prompt_tokens=10,
        completion_tokens=1,
        cost=0.01,
    )


@pytest.fixture
def mock_action_event():
    """Creates an ActionEvent for testing"""
    return ActionEvent(
        action_type="process_data",
        params={"input_file": "data.csv"},
        returns="100 rows processed",
        logs="Successfully processed all rows",
    )


@pytest.fixture
def mock_tool_event():
    """Creates a ToolEvent for testing"""
    return ToolEvent(
        name="searchWeb",
        params={"query": "python testing"},
        returns=["result1", "result2"],
        logs={"status": "success"},
    )


@pytest.fixture
def mock_error_event():
    """Creates an ErrorEvent for testing"""
    trigger = ActionEvent(action_type="risky_action")
    error = ValueError("Something went wrong")
    return ErrorEvent(
        trigger_event=trigger,
        exception=error,
        error_type="ValueError",
        details="Detailed error info"
    )


@pytest.fixture
def mock_span_exporter():
    """Creates an InMemorySpanExporter for testing"""
    return InMemorySpanExporter()


@pytest.fixture
def tracer_provider(mock_span_exporter):
    """Creates a TracerProvider with test exporter"""
    provider = TracerProvider()
    processor = SimpleSpanProcessor(mock_span_exporter)
    provider.add_span_processor(processor)
    return provider


@pytest.fixture(autouse=True)
def cleanup_telemetry():
    """Cleanup telemetry after each test"""
    yield
    # Clean up any active telemetry
    from agentops import Client
    client = Client()
    if hasattr(client, 'telemetry'):
        try:
            if client.telemetry._tracer_provider:
                client.telemetry._tracer_provider.shutdown()
            if client.telemetry._otel_manager:
                client.telemetry._otel_manager.shutdown()
            client.telemetry.shutdown()
        except Exception:
            pass  # Ensure cleanup continues even if one step fails
