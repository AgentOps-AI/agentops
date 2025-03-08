"""Tests for the LiveSpanProcessor class."""

import threading
from unittest.mock import MagicMock, patch

import pytest
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

from agentops.session.processors import LiveSpanProcessor


class TestLiveSpanProcessor:
    """Tests for the LiveSpanProcessor class."""

    def setUp(self):
        self.exporter = MagicMock(spec=SpanExporter)
        self.processor = LiveSpanProcessor(self.exporter)

    def test_init(self):
        """Test initialization of the processor."""
        exporter = MagicMock(spec=SpanExporter)
        processor = LiveSpanProcessor(exporter)

        assert processor._exporter == exporter
        assert processor._max_export_batch_size == 512
        assert processor._schedule_delay_millis == 5000
        assert processor._in_flight_spans == {}
        assert processor._shutdown is False
        assert isinstance(processor._lock, threading.Lock)

    def test_on_start(self):
        """Test on_start method (should do nothing)."""
        exporter = MagicMock(spec=SpanExporter)
        processor = LiveSpanProcessor(exporter)
        span = MagicMock(spec=ReadableSpan)

        # This should not raise any exceptions
        processor.on_start(span)

    def test_on_end(self):
        """Test on_end method adds span to in-flight spans."""
        exporter = MagicMock(spec=SpanExporter)
        processor = LiveSpanProcessor(exporter)
        span = MagicMock(spec=ReadableSpan)
        span.context.span_id = 12345

        processor.on_end(span)

        assert processor._in_flight_spans[12345] == span

    def test_on_end_after_shutdown(self):
        """Test on_end method doesn't add span after shutdown."""
        exporter = MagicMock(spec=SpanExporter)
        processor = LiveSpanProcessor(exporter)
        span = MagicMock(spec=ReadableSpan)
        span.context.span_id = 12345

        # Set shutdown flag
        processor._shutdown = True

        processor.on_end(span)

        assert 12345 not in processor._in_flight_spans

    def test_force_flush_empty(self):
        """Test force_flush with no spans."""
        exporter = MagicMock(spec=SpanExporter)
        processor = LiveSpanProcessor(exporter)

        processor.force_flush()

        exporter.export.assert_not_called()

    def test_force_flush(self):
        """Test force_flush with spans."""
        exporter = MagicMock(spec=SpanExporter)
        processor = LiveSpanProcessor(exporter)

        # Add spans to in-flight spans
        span1 = MagicMock(spec=ReadableSpan)
        span1.context.span_id = 12345
        span2 = MagicMock(spec=ReadableSpan)
        span2.context.span_id = 67890

        processor._in_flight_spans = {12345: span1, 67890: span2}

        processor.force_flush()

        # Verify spans were exported
        exporter.export.assert_called_once()
        exported_spans = exporter.export.call_args[0][0]
        assert len(exported_spans) == 2
        assert span1 in exported_spans
        assert span2 in exported_spans

        # Verify in-flight spans were cleared
        assert processor._in_flight_spans == {}

    def test_process_spans_empty(self):
        """Test _process_spans with no spans."""
        exporter = MagicMock(spec=SpanExporter)
        processor = LiveSpanProcessor(exporter)

        processor._process_spans(export_only=True)

        exporter.export.assert_not_called()

    def test_process_spans_success(self):
        """Test _process_spans with successful export."""
        exporter = MagicMock(spec=SpanExporter)
        exporter.export.return_value = SpanExportResult.SUCCESS
        processor = LiveSpanProcessor(exporter)

        span = MagicMock(spec=ReadableSpan)
        span.context.span_id = 12345
        processor._in_flight_spans = {12345: span}

        processor._process_spans(export_only=True)

        exporter.export.assert_called_once()

    def test_process_spans_failure(self):
        """Test _process_spans with failed export."""
        exporter = MagicMock(spec=SpanExporter)
        exporter.export.return_value = SpanExportResult.FAILURE
        processor = LiveSpanProcessor(exporter)

        span = MagicMock(spec=ReadableSpan)
        span.context.span_id = 12345
        processor._in_flight_spans = {12345: span}

        with patch("agentops.session.processors.logger") as mock_logger:
            processor._process_spans(export_only=True)

            mock_logger.warning.assert_called_once()

    def test_process_spans_exception(self):
        """Test _process_spans with exception."""
        exporter = MagicMock(spec=SpanExporter)
        exporter.export.side_effect = Exception("Test exception")
        processor = LiveSpanProcessor(exporter)

        span = MagicMock(spec=ReadableSpan)
        span.context.span_id = 12345
        processor._in_flight_spans = {12345: span}

        with patch("agentops.session.processors.logger") as mock_logger:
            processor._process_spans(export_only=True)

            mock_logger.warning.assert_called_once()

    def test_shutdown(self):
        """Test shutdown method."""
        exporter = MagicMock(spec=SpanExporter)
        processor = LiveSpanProcessor(exporter)

        span = MagicMock(spec=ReadableSpan)
        span.context.span_id = 12345
        processor._in_flight_spans = {12345: span}

        processor.shutdown()

        # Verify shutdown flag was set
        assert processor._shutdown is True

        # Verify spans were exported
        exporter.export.assert_called_once()

        # Verify in-flight spans were cleared
        assert processor._in_flight_spans == {}

        # Verify exporter was shut down
        exporter.shutdown.assert_called_once()

    def test_force_flush(self):
        """Test force_flush method."""
        exporter = MagicMock(spec=SpanExporter)
        exporter.force_flush = MagicMock(return_value=True)
        processor = LiveSpanProcessor(exporter)

        # Add a span to in-flight spans
        span = MagicMock(spec=ReadableSpan)
        span.context.span_id = 12345
        processor._in_flight_spans = {12345: span}

        result = processor.force_flush(timeout_millis=1000)

        # Verify spans were exported
        exporter.export.assert_called_once()

        # Verify exporter's force_flush was called
        exporter.force_flush.assert_called_once_with(1000)

        # Verify result is True
        assert result is True

    def test_force_flush_no_exporter_method(self):
        """Test force_flush when exporter doesn't have force_flush method."""
        exporter = MagicMock(spec=SpanExporter)
        # Ensure the exporter doesn't have a force_flush method
        if hasattr(exporter, "force_flush"):
            delattr(exporter, "force_flush")

        processor = LiveSpanProcessor(exporter)

        # Add a span to in-flight spans
        span = MagicMock(spec=ReadableSpan)
        span.context.span_id = 12345
        processor._in_flight_spans = {12345: span}

        result = processor.force_flush()

        # Verify spans were exported
        exporter.export.assert_called_once()

        # Verify result is True even though exporter doesn't have force_flush
        assert result is True

    def test_force_flush_exporter_exception(self):
        """Test force_flush when exporter's force_flush raises an exception."""
        exporter = MagicMock(spec=SpanExporter)
        exporter.force_flush = MagicMock(side_effect=Exception("Test exception"))
        processor = LiveSpanProcessor(exporter)

        # Add a span to in-flight spans
        span = MagicMock(spec=ReadableSpan)
        span.context.span_id = 12345
        processor._in_flight_spans = {12345: span}

        with patch("agentops.session.processors.logger") as mock_logger:
            result = processor.force_flush()

            # Verify warning was logged
            mock_logger.warning.assert_called_once()

            # Verify result is False due to exception
            assert result is False
