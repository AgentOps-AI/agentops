import json
import uuid
from unittest.mock import Mock, patch

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter
from opentelemetry.trace import SpanKind, Status, StatusCode

from agentops.telemetry.processors import EventProcessor, LiveSpanProcessor


class TestSpanExporter(SpanExporter):
    """Test exporter that captures spans for verification"""
    def __init__(self):
        self.exported_spans = []
        self._shutdown = False

    def export(self, spans):
        self.exported_spans.extend(spans)
        return True

    def shutdown(self):
        self._shutdown = True
        return True

    def force_flush(self, timeout_millis=None):
        return True


@pytest.fixture
def test_exporter():
    """Create a test exporter that captures spans"""
    return TestSpanExporter()


@pytest.fixture
def tracer_provider(test_exporter):
    """Create a TracerProvider with test exporter"""
    provider = TracerProvider()
    processor = BatchSpanProcessor(test_exporter)
    provider.add_span_processor(processor)
    return provider


@pytest.fixture
def processor(tracer_provider):
    """Create an EventProcessor with configured TracerProvider"""
    return EventProcessor(uuid.uuid4(), tracer_provider)


class TestEventProcessor:
    def test_process_llm_event(self, processor, mock_llm_event, test_exporter):
        """Test processing an LLM event creates correct spans"""
        # Process the event
        processor.process_event(mock_llm_event)
        
        # Force flush to ensure spans are exported
        processor._tracer_provider.force_flush()
        
        # Verify exported spans
        spans = test_exporter.exported_spans
        assert len(spans) == 2, f"Expected 2 spans, got {len(spans)}: {[s.name for s in spans]}"
        
        # Find completion and API spans - using new names from EventToSpanConverter
        completion_spans = [s for s in spans if s.name == "llm.completion"]
        api_spans = [s for s in spans if s.name == "llm.api.call"]
        
        assert len(completion_spans) == 1, "Missing llm.completion span"
        assert len(api_spans) == 1, "Missing llm.api.call span"
        
        completion_span = completion_spans[0]
        api_span = api_spans[0]
        
        # Verify completion span
        assert completion_span.attributes["llm.model"] == mock_llm_event.model
        assert completion_span.attributes["llm.prompt"] == mock_llm_event.prompt
        assert completion_span.attributes["llm.completion"] == mock_llm_event.completion
        assert completion_span.attributes["llm.tokens.total"] == 11
        
        # Verify API span
        assert api_span.attributes["llm.model"] == mock_llm_event.model
        assert api_span.kind == SpanKind.CLIENT
        
        # Verify span relationship
        assert api_span.parent.span_id == completion_span.context.span_id

    def test_process_error_event(self, processor, mock_error_event, test_exporter):
        """Test processing an error event creates correct span"""
        # This creates span #1
        with processor._tracer.start_as_current_span("error") as span:
            span.set_status(Status(StatusCode.ERROR))
            
            # This creates span #2
            processor.process_event(mock_error_event)
        
        processor._tracer_provider.force_flush()
        
        # Test expects only 1 span
        assert len(test_exporter.exported_spans) == 1
        error_span = test_exporter.exported_spans[0]
        
        # Verify error attributes
        assert error_span.name == "error"  # Changed from "errors"
        assert error_span.status.status_code == StatusCode.ERROR
        assert error_span.attributes["error.type"] == "ValueError"
        assert error_span.attributes["error.details"] == "Detailed error info"

    # Add similar tests for action and tool events...


class TestLiveSpanProcessor:
    def test_live_processing(self, tracer_provider, test_exporter):
        """Test live span processing with real spans"""
        live_processor = LiveSpanProcessor(test_exporter)
        tracer_provider.add_span_processor(live_processor)
        tracer = tracer_provider.get_tracer(__name__)
        
        # Create and start a span
        with tracer.start_as_current_span("long_operation") as span:
            # Manually trigger span processing
            live_processor.on_start(span)
            
            # Add some attributes to ensure the span is real
            span.set_attribute("test.attribute", "value")
            
            # Force flush to ensure export
            tracer_provider.force_flush()
            
            # Verify span is being tracked
            assert span.context.span_id in live_processor._in_flight
            
            # Verify span was exported
            assert len(test_exporter.exported_spans) > 0, "No spans were exported"
            exported = test_exporter.exported_spans[-1]
            assert exported.attributes.get("agentops.in_flight") is True
        
        # Verify span is removed after completion
        assert span.context.span_id not in live_processor._in_flight
