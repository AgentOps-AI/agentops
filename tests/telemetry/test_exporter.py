import json
import threading
import time
import uuid
from unittest.mock import Mock, patch

import pytest
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExportResult

from agentops.telemetry.exporter import ExportManager


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
def ref():
    return ExportManager(
        session_id=uuid.uuid4(), endpoint="http://test-endpoint/v2/create_events", jwt="test-jwt", api_key="test-key"
    )


class TestExportManager:
    def test_initialization(self, ref: ExportManager):
        """Test exporter initialization"""
        assert not ref._shutdown.is_set()
        assert isinstance(ref._export_lock, type(threading.Lock()))
        assert ref._retry_count == 3
        assert ref._retry_delay == 1.0

    def test_export_empty_spans(self, ref):
        """Test exporting empty spans list"""
        result = ref.export([])
        assert result == SpanExportResult.SUCCESS

    def test_export_single_span(self, ref, mock_span):
        """Test exporting a single span"""
        with patch("agentops.http_client.HttpClient.post") as mock_post:
            mock_post.return_value.code = 200

            result = ref.export([mock_span])
            assert result == SpanExportResult.SUCCESS

            # Verify request
            mock_post.assert_called_once()
            call_args = mock_post.call_args[0]
            payload = json.loads(call_args[1].decode("utf-8"))

            assert len(payload["events"]) == 1
            assert payload["events"][0]["event_type"] == "test_span"

    def test_export_multiple_spans(self, ref, mock_span):
        """Test exporting multiple spans"""
        spans = [mock_span, mock_span]

        with patch("agentops.http_client.HttpClient.post") as mock_post:
            mock_post.return_value.code = 200

            result = ref.export(spans)
            assert result == SpanExportResult.SUCCESS

            # Verify request
            mock_post.assert_called_once()
            call_args = mock_post.call_args[0]
            payload = json.loads(call_args[1].decode("utf-8"))

            assert len(payload["events"]) == 2

    def test_export_failure_retry(self, ref, mock_span):
        """Test retry behavior on export failure"""
        mock_wait = Mock()
        ref._set_wait_fn(mock_wait)  # Use the test helper
        
        with patch("agentops.http_client.HttpClient.post") as mock_post:
            # First two calls fail, third succeeds
            mock_post.side_effect = [Mock(code=500), Mock(code=500), Mock(code=200)]

            result = ref.export([mock_span])
            assert result == SpanExportResult.SUCCESS
            assert mock_post.call_count == 3

            # Verify exponential backoff delays
            assert mock_wait.call_count == 2
            assert mock_wait.call_args_list[0][0][0] == 1.0
            assert mock_wait.call_args_list[1][0][0] == 2.0

    def test_export_max_retries_exceeded(self, ref, mock_span):
        """Test behavior when max retries are exceeded"""
        mock_wait = Mock()
        ref._set_wait_fn(mock_wait)
        
        with patch("agentops.http_client.HttpClient.post") as mock_post:
            mock_post.return_value.code = 500

            result = ref.export([mock_span])
            assert result == SpanExportResult.FAILURE
            assert mock_post.call_count == ref._retry_count
            
            # Verify all retries waited
            assert mock_wait.call_count == ref._retry_count - 1  # One less wait than attempts

    def test_shutdown_behavior(self, ref, mock_span):
        """Test exporter shutdown behavior"""
        ref.shutdown()
        assert ref._shutdown.is_set()

        # Should return success without exporting
        result = ref.export([mock_span])
        assert result == SpanExportResult.SUCCESS

    def test_malformed_span_handling(self, ref):
        """Test handling of malformed spans"""
        malformed_span = Mock(spec=ReadableSpan)
        malformed_span.name = "test_span"
        malformed_span.attributes = {}  # Missing required attributes

        with patch("agentops.http_client.HttpClient.post") as mock_post:
            mock_post.return_value.code = 200

            result = ref.export([malformed_span])
            assert result == SpanExportResult.SUCCESS

            # Verify event was formatted with defaults
            call_args = mock_post.call_args[0]
            payload = json.loads(call_args[1].decode("utf-8"))
            event = payload["events"][0]

            assert "id" in event
            assert event["event_type"] == "test_span"

    def test_concurrent_exports(self, ref, mock_span):
        """Test concurrent export handling"""

        def export_spans():
            return ref.export([mock_span])

        with patch("agentops.http_client.HttpClient.post") as mock_post:
            mock_post.return_value.code = 200

            # Create and start threads
            threads = [threading.Thread(target=export_spans) for _ in range(3)]
            for thread in threads:
                thread.start()

            # Wait for all threads to complete
            for thread in threads:
                thread.join()

            # Verify each thread's export was processed
            assert mock_post.call_count == 3
