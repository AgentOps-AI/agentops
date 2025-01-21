from unittest.mock import Mock, patch
from typing import List, Any

import pytest
from opentelemetry.sdk.trace import ReadableSpan, Span
from opentelemetry.trace import SpanContext, TraceFlags, Status, StatusCode
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.context import Context

from agentops.telemetry.processors import SessionSpanProcessor


@pytest.fixture
def mock_span_exporter() -> Mock:
    """Create a mock span exporter"""
    return Mock()


def create_mock_span(span_id: int = 123) -> Mock:
    """Helper to create consistent mock spans"""
    span = Mock(spec=Span)
    span.context = Mock(spec=SpanContext, span_id=span_id, trace_flags=TraceFlags(TraceFlags.SAMPLED))

    # Set up attributes dict and methods
    span.attributes = {}

    def set_attributes(attrs: dict) -> None:
        span.attributes.update(attrs)

    def set_attribute(key: str, value: Any) -> None:
        span.attributes[key] = value

    span.set_attributes = Mock(side_effect=set_attributes)
    span.set_attribute = Mock(side_effect=set_attribute)

    span.is_recording.return_value = True
    span.set_status = Mock()

    # Set up readable span
    mock_readable = Mock(spec=ReadableSpan)
    mock_readable.attributes = span.attributes
    mock_readable.context = span.context
    span._readable_span.return_value = mock_readable

    return span


@pytest.fixture
def mock_span() -> Mock:
    """Create a mock span with proper attribute handling"""
    return create_mock_span()


@pytest.fixture
def processor(mock_span_exporter) -> SessionSpanProcessor:
    """Create a processor for testing"""
    batch_processor = BatchSpanProcessor(mock_span_exporter)
    return SessionSpanProcessor(session_id=123, processor=batch_processor)


class TestSessionSpanProcessor:
    def test_initialization(self, processor: SessionSpanProcessor, mock_span_exporter: Mock) -> None:
        """Test processor initialization"""
        assert processor.session_id == 123
        assert isinstance(processor.processor, BatchSpanProcessor)
        assert processor.event_counts == {
            "llms": 0,
            "tools": 0,
            "actions": 0,
            "errors": 0,
            "apis": 0,
        }

    def test_span_processing_lifecycle(self, processor: SessionSpanProcessor, mock_span: Mock) -> None:
        """Test complete span lifecycle"""
        mock_span.attributes["event.type"] = "llms"

        processor.on_start(mock_span)

        assert mock_span.set_attributes.called
        assert mock_span.attributes["session.id"] == str(processor.session_id)
        assert "event.timestamp" in mock_span.attributes
        assert processor.event_counts["llms"] == 1

        readable_span = mock_span._readable_span()
        processor.on_end(readable_span)

    def test_unsampled_span_ignored(self, processor: SessionSpanProcessor) -> None:
        """Test that unsampled spans are ignored"""
        unsampled_span = Mock(spec=Span)
        unsampled_span.context = Mock(spec=SpanContext, trace_flags=TraceFlags(TraceFlags.DEFAULT))
        unsampled_span.is_recording.return_value = False

        processor.on_start(unsampled_span)
        assert not unsampled_span.set_attributes.called

    def test_span_without_context(self, processor: SessionSpanProcessor) -> None:
        """Test handling of spans without context"""
        span_without_context = Mock(spec=Span)
        span_without_context.context = None
        span_without_context.is_recording.return_value = True
        span_without_context.attributes = {}

        # Should not raise exception and should not call wrapped processor
        processor.on_start(span_without_context)

        # Create readable span without context
        readable_span = Mock(spec=ReadableSpan)
        readable_span.context = None
        readable_span.attributes = span_without_context.attributes

        # Should not raise exception and should not call wrapped processor
        with patch.object(processor.processor, "on_end") as mock_on_end:
            processor.on_end(readable_span)
            mock_on_end.assert_not_called()

        # Verify processor still works after handling None context
        normal_span = create_mock_span()
        with patch.object(processor.processor, "on_start") as mock_on_start:
            processor.on_start(normal_span)
            mock_on_start.assert_called_once_with(normal_span, None)

        with patch.object(processor.processor, "on_end") as mock_on_end:
            processor.on_end(normal_span._readable_span())
            mock_on_end.assert_called_once_with(normal_span._readable_span())

    def test_concurrent_spans(self, processor: SessionSpanProcessor) -> None:
        """Test handling multiple spans concurrently"""
        spans: List[Mock] = [create_mock_span(i) for i in range(3)]

        for span in spans:
            processor.on_start(span)
            assert span.attributes["session.id"] == str(processor.session_id)

        for span in reversed(spans):
            processor.on_end(span._readable_span())

    def test_error_span_handling(self, processor: SessionSpanProcessor) -> None:
        """Test handling of error spans"""
        # Create parent span with proper attribute handling
        parent_span = create_mock_span(1)

        # Create error span
        error_span = create_mock_span(2)
        error_span.attributes.update({"error": True, "error.type": "ValueError", "error.message": "Test error"})

        with patch("opentelemetry.trace.get_current_span", return_value=parent_span):
            processor.on_end(error_span._readable_span())

            # Verify status was set
            assert parent_span.set_status.called
            status_args = parent_span.set_status.call_args[0][0]
            assert status_args.status_code == StatusCode.ERROR

            # Verify error attributes were set correctly
            assert parent_span.set_attribute.call_args_list == [
                (("error.type", "ValueError"), {}),
                (("error.message", "Test error"), {}),
            ]

    def test_event_counting(self, processor: SessionSpanProcessor) -> None:
        """Test event counting for different event types"""
        for event_type in processor.event_counts.keys():
            span = create_mock_span()
            span.attributes["event.type"] = event_type

            processor.on_start(span)
            assert processor.event_counts[event_type] == 1

    def test_processor_shutdown(self, processor: SessionSpanProcessor) -> None:
        """Test processor shutdown"""
        with patch.object(processor.processor, "shutdown") as mock_shutdown:
            processor.shutdown()
            mock_shutdown.assert_called_once()

    def test_force_flush(self, processor: SessionSpanProcessor) -> None:
        """Test force flush"""
        with patch.object(processor.processor, "force_flush") as mock_flush:
            mock_flush.return_value = True
            assert processor.force_flush() is True
            mock_flush.assert_called_once()

    def test_span_attributes_preserved(self, processor: SessionSpanProcessor, mock_span: Mock) -> None:
        """Test that existing span attributes are preserved"""
        mock_span.attributes = {"custom.attr": "value"}
        processor.on_start(mock_span)

        assert mock_span.attributes["custom.attr"] == "value"
        assert mock_span.attributes["session.id"] == str(processor.session_id)
