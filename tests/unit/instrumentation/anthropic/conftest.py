import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock
from opentelemetry.trace import Span, SpanContext
from opentelemetry.metrics import Meter

# Load fixture data
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def load_fixture(filename):
    """Load a JSON fixture file"""
    with open(FIXTURES_DIR / filename) as f:
        return json.load(f)


@pytest.fixture
def mock_tracer():
    """Create a mock OpenTelemetry tracer with configured span and context"""
    tracer = MagicMock()
    span = MagicMock(spec=Span)
    span_context = MagicMock(spec=SpanContext)
    span.get_span_context.return_value = span_context
    tracer.start_span.return_value = span
    return tracer


@pytest.fixture
def mock_meter():
    """Create a mock OpenTelemetry meter with histogram and counter"""
    meter = MagicMock(spec=Meter)
    histogram = MagicMock()
    counter = MagicMock()
    meter.create_histogram.return_value = histogram
    meter.create_counter.return_value = counter
    return meter


@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client with configured message and stream responses"""
    client = MagicMock()
    message_response = load_fixture("anthropic_message.json")
    client.messages.create.return_value = MagicMock(**message_response)

    stream_response = load_fixture("anthropic_stream.json")
    stream_manager = MagicMock()
    stream_manager.__enter__.return_value = MagicMock(
        text_stream=iter(stream_response["messages"]),
        _MessageStreamManager__stream=MagicMock(
            _MessageStream__final_message_snapshot=MagicMock(**stream_response["final_message"])
        ),
    )
    client.messages.stream.return_value = stream_manager
    return client


@pytest.fixture
def mock_event_handler():
    """Create a mock event handler with all required event handling methods"""
    handler = MagicMock()
    handler.on_event = MagicMock()
    handler.on_text_delta = MagicMock()
    handler.on_content_block_start = MagicMock()
    handler.on_content_block_delta = MagicMock()
    handler.on_content_block_stop = MagicMock()
    handler.on_message_start = MagicMock()
    handler.on_message_delta = MagicMock()
    handler.on_message_stop = MagicMock()
    handler.on_error = MagicMock()
    return handler


@pytest.fixture
def mock_stream_manager():
    """Create a mock stream manager that emits events during text streaming"""
    manager = MagicMock()
    stream = MagicMock()

    def text_stream_iter():
        chunks = ["1", "2", "3", "4", "5"]
        for chunk in chunks:
            if hasattr(stream, "event_handler") and stream.event_handler is not None:
                stream.event_handler.on_text_delta({"text": chunk}, {"text": chunk})
            yield chunk

    stream.text_stream = text_stream_iter()
    manager.__enter__.return_value = stream
    return manager


@pytest.fixture
def mock_async_stream_manager():
    """Create a mock async stream manager with async iteration support"""
    manager = MagicMock()
    stream = MagicMock()
    stream.text_stream = MagicMock()
    stream.text_stream.__aiter__.return_value = iter(["1", "2", "3", "4", "5"])
    manager.__aenter__.return_value = stream
    return manager


@pytest.fixture
def mock_stream_event():
    """Fixture for a mock streaming event."""

    class MockMessageStartEvent:
        def __init__(self):
            self.message = type("obj", (object,), {"id": "msg_123", "model": "claude-3-opus-20240229"})
            self.__class__.__name__ = "MessageStartEvent"

    return MockMessageStartEvent()


@pytest.fixture
def mock_message_stop_event():
    """Fixture for a mock message stop event."""

    class MockMessageStopEvent:
        def __init__(self):
            self.message = type("obj", (object,), {"stop_reason": "stop_sequence"})
            self.__class__.__name__ = "MessageStopEvent"

    return MockMessageStopEvent()


@pytest.fixture
def mock_tool_definition():
    """Fixture for a mock tool definition."""
    return [
        {
            "name": "calculator",
            "description": "A simple calculator",
            "input_schema": {
                "type": "object",
                "properties": {"operation": {"type": "string"}, "numbers": {"type": "array"}},
            },
        }
    ]


@pytest.fixture
def mock_tool_use_content():
    """Fixture for mock tool use content."""

    class MockToolUseBlock:
        def __init__(self):
            self.type = "tool_use"
            self.name = "calculator"
            self.id = "tool_123"
            self.input = {"operation": "add", "numbers": [1, 2]}

    return [MockToolUseBlock()]
