import pytest
from uuid import uuid4
from opentelemetry.trace import SpanKind, Status, StatusCode
from opentelemetry.sdk.trace import TracerProvider, Span
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from agentops.telemetry.processors import EventProcessor
from agentops.event import LLMEvent, ActionEvent, ToolEvent, ErrorEvent


@pytest.fixture
def wrapped_processor():
    """Create a simple processor for testing"""
    return SimpleSpanProcessor(mock_span_exporter())


@pytest.fixture
def event_processor(session_id, wrapped_processor):
    """Create an EventProcessor instance for testing"""
    return EventProcessor(
        session_id=session_id,
        processor=wrapped_processor
    )


class TestEventProcessor:
    """Test suite for EventProcessor class"""

    def test_on_start_adds_session_context(self, event_processor, tracer_provider):
        """Test that on_start adds session context and attributes"""
        tracer = tracer_provider.get_tracer(__name__)
        
        with tracer.start_span("test") as span:
            event_processor.on_start(span)
            
            assert span.attributes.get("session.id") == str(event_processor.session_id)
            assert "event.timestamp" in span.attributes

    def test_on_start_updates_event_counts(self, event_processor, tracer_provider):
        """Test that on_start updates event counts for AgentOps events"""
        tracer = tracer_provider.get_tracer(__name__)
        
        with tracer.start_span("test", attributes={"event.type": "llms"}) as span:
            event_processor.on_start(span)
            
            assert event_processor.event_counts["llms"] == 1

    def test_on_end_handles_error_events(self, event_processor, tracer_provider):
        """Test that on_end properly handles error events"""
        tracer = tracer_provider.get_tracer(__name__)
        
        with tracer.start_span("parent") as parent:
            with tracer.start_span(
                "error", 
                attributes={
                    "error": True,
                    "error.type": "ValueError",
                    "error.message": "Test error"
                }
            ) as error_span:
                event_processor.on_end(error_span)
                
                assert parent.status.status_code == StatusCode.ERROR
                assert parent.attributes.get("error.type") == "ValueError"
                assert parent.attributes.get("error.message") == "Test error"

    def test_shutdown_and_flush(self, event_processor, wrapped_processor):
        """Test shutdown and flush are forwarded to wrapped processor"""
        event_processor.shutdown()
        assert wrapped_processor.shutdown.called

        event_processor.force_flush()
        assert wrapped_processor.force_flush.called 