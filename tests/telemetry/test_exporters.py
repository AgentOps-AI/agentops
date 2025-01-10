import json
import threading
import time
import uuid
from unittest.mock import Mock, patch

import pytest
from uuid import UUID
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.trace import SpanKind, Status, StatusCode
from opentelemetry.sdk.trace.export import SpanExportResult

from agentops.telemetry.exporters.event import EventExporter
from agentops.telemetry.exporters.session import SessionExporter


@pytest.fixture
def mock_span():
    span = Mock(spec=ReadableSpan)
    span.name = "test_span"
    span.attributes = {
        "event.id": str(uuid.uuid4()),
        "event.data": json.dumps({"test": "data"}),
        "event.timestamp": "2024-01-01T00:00:00Z",
        "event.end_timestamp": "2024-01-01T00:00:01Z",
    }
    return span


@pytest.fixture
def event_exporter():
    return EventExporter(
        session_id=uuid.uuid4(), 
        endpoint="http://test-endpoint/v2/create_events", 
        jwt="test-jwt", 
        api_key="test-key"
    )


class TestEventExporter:
    """Test suite for EventExporter"""

    def test_initialization(self, event_exporter: EventExporter):
        """Test exporter initialization"""
        assert not event_exporter._shutdown.is_set()
        assert isinstance(event_exporter._export_lock, type(threading.Lock()))
        assert event_exporter._retry_count == 3
        assert event_exporter._retry_delay == 1.0

    def test_export_empty_spans(self, event_exporter):
        """Test exporting empty spans list"""
        result = event_exporter.export([])
        assert result == SpanExportResult.SUCCESS

    def test_export_single_span(self, event_exporter, mock_span):
        """Test exporting a single span"""
        with patch("agentops.http_client.HttpClient.post") as mock_post:
            mock_post.return_value.code = 200

            result = event_exporter.export([mock_span])
            assert result == SpanExportResult.SUCCESS

            # Verify request
            mock_post.assert_called_once()
            call_args = mock_post.call_args[0]
            payload = json.loads(call_args[1].decode("utf-8"))

            assert len(payload["events"]) == 1
            assert payload["events"][0]["event_type"] == "test_span"

    def test_export_multiple_spans(self, event_exporter, mock_span):
        """Test exporting multiple spans"""
        spans = [mock_span, mock_span]

        with patch("agentops.http_client.HttpClient.post") as mock_post:
            mock_post.return_value.code = 200

            result = event_exporter.export(spans)
            assert result == SpanExportResult.SUCCESS

            # Verify request
            mock_post.assert_called_once()
            call_args = mock_post.call_args[0]
            payload = json.loads(call_args[1].decode("utf-8"))

            assert len(payload["events"]) == 2

    def test_export_failure_retry(self, event_exporter, mock_span):
        """Test retry behavior on export failure"""
        mock_wait = Mock()
        event_exporter._wait_fn = mock_wait
        
        with patch("agentops.http_client.HttpClient.post") as mock_post:
            # Create mock responses with proper return values
            mock_responses = [
                Mock(code=500),  # First attempt fails
                Mock(code=500),  # Second attempt fails
                Mock(code=200),  # Third attempt succeeds
            ]
            mock_post.side_effect = mock_responses

            result = event_exporter.export([mock_span])
            assert result == SpanExportResult.SUCCESS
            assert mock_post.call_count == 3

            # Verify exponential backoff delays
            assert mock_wait.call_count == 2
            assert mock_wait.call_args_list[0][0][0] == 1.0
            assert mock_wait.call_args_list[1][0][0] == 2.0

    def test_export_max_retries_exceeded(self, event_exporter, mock_span):
        """Test behavior when max retries are exceeded"""
        mock_wait = Mock()
        event_exporter._wait_fn = mock_wait
        
        with patch("agentops.http_client.HttpClient.post") as mock_post:
            # Mock consistently failing response
            mock_response = Mock(code=500)
            mock_post.return_value = mock_response

            result = event_exporter.export([mock_span])
            assert result == SpanExportResult.FAILURE
            assert mock_post.call_count == event_exporter._retry_count
            
            # Verify all retries waited
            assert mock_wait.call_count == event_exporter._retry_count - 1

    def test_shutdown_behavior(self, event_exporter, mock_span):
        """Test exporter shutdown behavior"""
        event_exporter.shutdown()
        assert event_exporter._shutdown.is_set()

        # Should return success without exporting
        result = event_exporter.export([mock_span])
        assert result == SpanExportResult.SUCCESS

    def test_retry_logic(self, exporter, test_span):
        """Verify retry behavior works as expected"""
        with patch("agentops.http_client.HttpClient.post") as mock_post:
            # Create mock responses with proper return values
            mock_responses = [
                Mock(code=500),  # First attempt fails
                Mock(code=500),  # Second attempt fails
                Mock(code=200),  # Third attempt succeeds
            ]
            mock_post.side_effect = mock_responses
            
            result = exporter.export([test_span])
            assert result == SpanExportResult.SUCCESS
            assert mock_post.call_count == 3

            # Verify the endpoint was called correctly
            for call in mock_post.call_args_list:
                assert call[0][0] == exporter.endpoint
                payload = json.loads(call[0][1].decode("utf-8"))
                assert "events" in payload
                assert len(payload["events"]) == 1


class TestSessionExporter:
    """Test suite for SessionExporter"""
    
    @pytest.fixture
    def test_span(self):
        """Create a test span with required attributes"""
        span = Mock(spec=ReadableSpan)
        span.name = "test_span"
        span.attributes = {
            "event.id": str(uuid.uuid4()),
            "event.data": json.dumps({"test": "data"}),
            "event.timestamp": "2024-01-01T00:00:00Z",
            "event.end_timestamp": "2024-01-01T00:00:01Z",
        }
        return span
    
    @pytest.fixture
    def exporter(self):
        """Create a SessionExporter with mocked session"""
        from agentops.session import Session
        mock_config = Mock()
        mock_config.endpoint = "http://test"
        mock_config.api_key = "test-key"
        
        mock_session = Mock(spec=Session)
        mock_session.session_id = UUID('00000000-0000-0000-0000-000000000000')
        mock_session.jwt = "test-jwt"
        mock_session.config = mock_config
        
        return SessionExporter(session=mock_session)

    def test_event_formatting(self, exporter, test_span):
        """Verify events are formatted correctly"""
        with patch("agentops.http_client.HttpClient.post") as mock_post:
            mock_post.return_value.code = 200
            result = exporter.export([test_span])
            assert result == SpanExportResult.SUCCESS
            
            # Verify the formatted event
            call_args = mock_post.call_args[0]
            payload = json.loads(call_args[1].decode("utf-8"))
            assert len(payload["events"]) == 1
            event = payload["events"][0]
            assert "id" in event
            assert "event_type" in event
            assert "session_id" in event

    def test_retry_logic(self, exporter, test_span):
        """Verify retry behavior works as expected"""
        with patch("agentops.http_client.HttpClient.post") as mock_post:
            mock_responses = [
                Mock(code=500),  # First attempt fails
                Mock(code=500),  # Second attempt fails
                Mock(code=200),  # Third attempt succeeds
            ]
            mock_post.side_effect = mock_responses
            
            result = exporter.export([test_span])
            assert result == SpanExportResult.SUCCESS
            assert mock_post.call_count == 3

    def test_batch_processing(self, exporter, test_span):
        """Verify batch processing works correctly"""
        with patch("agentops.http_client.HttpClient.post") as mock_post:
            mock_post.return_value.code = 200
            spans = [test_span for _ in range(5)]
            result = exporter.export(spans)
            assert result == SpanExportResult.SUCCESS
            
            # Verify batch was sent correctly
            call_args = mock_post.call_args[0]
            payload = json.loads(call_args[1].decode("utf-8"))
            assert len(payload["events"]) == 5 