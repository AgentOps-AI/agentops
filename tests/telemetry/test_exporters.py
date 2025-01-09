import pytest
from uuid import UUID
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.trace import SpanKind, Status, StatusCode
from opentelemetry.sdk.trace.export import SpanExportResult

from agentops.telemetry.exporters.session import SessionExporter

class TestSessionExporter:
    """Test suite for new SessionExporter"""
    
    @pytest.fixture
    def exporter(self):
        return SessionExporter(
            session_id=UUID('00000000-0000-0000-0000-000000000000'),
            jwt="test-jwt",
            endpoint="http://test",
            api_key="test-key"
        )

    def test_event_formatting(self, exporter, test_span):
        """Verify events are formatted correctly"""
        formatted = exporter._format_spans([test_span])
        
        assert len(formatted) == 1
        event = formatted[0]
        assert "id" in event
        assert "event_type" in event
        assert "session_id" in event

    def test_retry_logic(self, exporter, test_span, mocker):
        """Verify retry behavior works as expected"""
        mock_send = mocker.patch.object(exporter, '_send_batch')
        mock_send.side_effect = [False, False, True]
        
        result = exporter.export([test_span])
        assert result == SpanExportResult.SUCCESS
        assert mock_send.call_count == 3

    def test_batch_processing(self, exporter, test_span):
        """Verify batch processing works correctly"""
        spans = [test_span for _ in range(5)]
        result = exporter.export(spans)
        assert result == SpanExportResult.SUCCESS 