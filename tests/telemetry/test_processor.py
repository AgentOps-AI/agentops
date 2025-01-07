import json
import time
import uuid
from contextlib import contextmanager
from unittest.mock import Mock, patch

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import SpanContext, TraceFlags

from agentops.enums import EventType
from agentops.telemetry.client import ClientTelemetry
from agentops.telemetry.manager import OTELManager
from agentops.telemetry.processors import EventProcessor, LiveSpanProcessor
from agentops.telemetry.converter import EventToSpanConverter, SpanDefinition


@pytest.fixture
def mock_tracer(test_span):
    """Create a mock TracerProvider that returns a mock Tracer"""
    tracer = Mock(spec=trace.Tracer)

    @contextmanager
    def mock_span_context(name, attributes=None, **kwargs):
        span = test_span(name, attributes)
        yield span

    tracer.start_as_current_span = mock_span_context
    
    provider = Mock(spec=TracerProvider)
    provider.get_tracer = Mock(return_value=tracer)
    return provider


@pytest.fixture
def processor(mock_tracer):
    """Create an EventProcessor with a mock TracerProvider"""
    return EventProcessor(uuid.uuid4(), mock_tracer)


@pytest.fixture
def mock_span_exporter():
    return Mock()


@pytest.fixture
def live_processor(mock_span_exporter):
    return LiveSpanProcessor(mock_span_exporter)


class TestEventProcessor:
    def test_initialization(self, processor):
        """Test processor initialization"""
        expected_counts = {
            "llms": 0,
            "tools": 0,
            "actions": 0,
            "errors": 0,
            "apis": 0,
        }
        assert processor.event_counts == expected_counts

    def test_process_action_event(self, processor, mock_action_event):
        """Test processing an action event"""
        span = processor.process_event(mock_action_event)

        assert span is not None
        assert processor.event_counts["actions"] == 1

        event_data = json.loads(span._attributes["event.data"])
        assert event_data["action_type"] == "process_data"
        assert event_data["params"] == {"input_file": "data.csv"}
        assert event_data["returns"] == "100 rows processed"
        assert event_data["logs"] == "Successfully processed all rows"

    def test_process_llm_event(self, processor, mock_llm_event):
        """Test processing an LLM event"""
        span = processor.process_event(mock_llm_event)

        assert span is not None
        assert processor.event_counts["llms"] == 1

        event_data = json.loads(span._attributes["event.data"])
        assert event_data["prompt"] == "What is the meaning of life?"
        assert event_data["completion"] == "42"
        assert event_data["model"] == "gpt-4"
        assert event_data["prompt_tokens"] == 10
        assert event_data["completion_tokens"] == 1
        assert event_data["cost"] == 0.01

    def test_process_tool_event(self, processor, mock_tool_event):
        """Test processing a tool event"""
        span = processor.process_event(mock_tool_event)

        assert span is not None
        assert processor.event_counts["tools"] == 1

        event_data = json.loads(span._attributes["event.data"])
        assert event_data["name"] == "searchWeb"
        assert event_data["params"]["query"] == "python testing"
        assert event_data["returns"] == ["result1", "result2"]
        assert event_data["logs"] == {"status": "success"}

    def test_process_error_event(self, processor, mock_error_event):
        """Test processing an error event"""
        span = processor.process_event(mock_error_event)

        assert span is not None
        assert processor.event_counts["errors"] == 1
        assert span._attributes["error"] is True

        event_data = json.loads(span._attributes["event.data"])
        assert event_data["error_type"] == "ValueError"
        assert event_data["details"] == "Detailed error info"
        assert "trigger_event" in event_data

    def test_long_running_event(self, processor, live_processor, mock_span_exporter, test_span):
        """Test processing of long-running events with LiveSpanProcessor"""
        # Create a test span
        mock_span = test_span("llms")
        tracer = Mock(spec=trace.Tracer)

        @contextmanager
        def mock_span_context(name, attributes=None, **kwargs):
            mock_span._attributes = attributes or {}
            yield mock_span
            live_processor.on_start(mock_span)

        tracer.start_as_current_span = mock_span_context

        provider = Mock(spec=TracerProvider)
        provider.get_tracer = Mock(return_value=tracer)
        provider.add_span_processor(live_processor)

        processor._tracer_provider = provider
        processor._tracer = tracer

        # Process event
        span = processor.process_event(mock_llm_event)

        assert span is not None
        assert processor.event_counts["llms"] == 1
        assert span.context.span_id in live_processor._in_flight


class TestLiveSpanProcessor:
    def test_initialization(self, live_processor, mock_span_exporter):
        """Test processor initialization"""
        assert live_processor.span_exporter == mock_span_exporter
        assert live_processor._in_flight == {}
        assert not live_processor._stop_event.is_set()
        assert live_processor._export_thread.daemon
        assert live_processor._export_thread.is_alive()

    def test_span_processing_lifecycle(self, live_processor, test_span):
        """Test complete span lifecycle"""
        # Create and start span
        span = test_span("test_span")
        live_processor.on_start(span)
        assert span.context.span_id in live_processor._in_flight

        # End span
        live_processor.on_end(span)
        assert span.context.span_id not in live_processor._in_flight
        live_processor.span_exporter.export.assert_called_once()

    def test_unsampled_span_ignored(self, live_processor, test_span):
        """Test that unsampled spans are ignored"""
        span = test_span("test_span")
        span.context = SpanContext(
            trace_id=uuid.uuid4().int & ((1 << 128) - 1),
            span_id=uuid.uuid4().int & ((1 << 64) - 1),
            trace_flags=TraceFlags(TraceFlags.DEFAULT),
            is_remote=False,
        )

        live_processor.on_start(span)
        assert len(live_processor._in_flight) == 0

        live_processor.on_end(span)
        live_processor.span_exporter.export.assert_not_called()

    @patch("time.sleep")
    def test_periodic_export(self, mock_sleep, live_processor, test_span):
        """Test periodic export of in-flight spans"""
        span = test_span("test_span")
        live_processor.on_start(span)

        with live_processor._lock:
            to_export = [span]
            if to_export:
                live_processor.span_exporter.export(to_export)

        exported_span = live_processor.span_exporter.export.call_args[0][0][0]
        assert exported_span._attributes.get("agentops.in_flight") is True
        assert "agentops.duration_ms" in exported_span._attributes

    def test_concurrent_spans(self, live_processor, test_span):
        """Test handling multiple concurrent spans"""
        spans = [test_span(f"span_{i}") for i in range(3)]

        # Start all spans
        for span in spans:
            live_processor.on_start(span)
        assert len(live_processor._in_flight) == 3

        # End all spans
        for span in reversed(spans):
            live_processor.on_end(span)
        assert len(live_processor._in_flight) == 0

    def test_shutdown(self, live_processor):
        """Test processor shutdown"""
        live_processor.shutdown()
        assert live_processor._stop_event.is_set()
        assert not live_processor._export_thread.is_alive()
        live_processor.span_exporter.shutdown.assert_called_once()
