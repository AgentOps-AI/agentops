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
        session_id=uuid.uuid4(), endpoint="http://test-endpoint/v2/create_events", jwt="test-jwt", api_key="test-key"
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
        with patch("agentops.session.api.SessionApiClient.create_events") as mock_create:
            mock_create.return_value = True

            result = event_exporter.export([mock_span])
            assert result == SpanExportResult.SUCCESS

            # Verify request
            mock_create.assert_called_once()
            call_args = mock_create.call_args[0]
            events = call_args[0]

            assert len(events) == 1
            assert events[0]["event_type"] == "test_span"

    def test_export_multiple_spans(self, event_exporter, mock_span):
        """Test exporting multiple spans"""
        spans = [mock_span, mock_span]

        with patch("agentops.session.api.SessionApiClient.create_events") as mock_create:
            mock_create.return_value = True

            result = event_exporter.export(spans)
            assert result == SpanExportResult.SUCCESS

            # Verify request
            mock_create.assert_called_once()
            call_args = mock_create.call_args[0]
            events = call_args[0]

            assert len(events) == 2

    def test_export_failure_retry(self, event_exporter, mock_span):
        """Test retry behavior on export failure"""
        mock_wait = Mock()
        event_exporter._wait_fn = mock_wait

        with patch("agentops.session.api.SessionApiClient.create_events") as mock_create:
            # Create mock responses with proper return values
            mock_create.side_effect = [False, False, True]

            result = event_exporter.export([mock_span])
            assert result == SpanExportResult.SUCCESS
            assert mock_create.call_count == 3

            # Verify exponential backoff delays
            assert mock_wait.call_count == 2
            assert mock_wait.call_args_list[0][0][0] == 1.0
            assert mock_wait.call_args_list[1][0][0] == 2.0

    def test_export_max_retries_exceeded(self, event_exporter, mock_span):
        """Test behavior when max retries are exceeded"""
        mock_wait = Mock()
        event_exporter._wait_fn = mock_wait

        with patch("agentops.session.api.SessionApiClient.create_events") as mock_create:
            # Mock consistently failing response
            mock_create.return_value = False

            result = event_exporter.export([mock_span])
            assert result == SpanExportResult.FAILURE
            assert mock_create.call_count == event_exporter._retry_count

            # Verify all retries waited
            assert mock_wait.call_count == event_exporter._retry_count - 1

    def test_shutdown_behavior(self, event_exporter, mock_span):
        """Test exporter shutdown behavior"""
        event_exporter.shutdown()
        assert event_exporter._shutdown.is_set()

        # Should return success without exporting
        result = event_exporter.export([mock_span])
        assert result == SpanExportResult.SUCCESS

    def test_retry_logic(self, event_exporter, mock_span):
        """Verify retry behavior works as expected"""
        with patch("agentops.session.api.SessionApiClient.create_events") as mock_create:
            # Create mock responses with proper return values
            mock_create.side_effect = [False, False, True]

            result = event_exporter.export([mock_span])
            assert result == SpanExportResult.SUCCESS
            assert mock_create.call_count == 3

            # Verify the events were sent correctly
            for call in mock_create.call_args_list:
                events = call[0][0]
                assert len(events) == 1
                assert "event_type" in events[0]
                assert events[0]["event_type"] == "test_span"


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
    def session_exporter(self):
        """Create a SessionExporter instance for testing"""
        from agentops.session import Session
        from agentops.session.api import SessionApiClient

        mock_config = Mock()
        mock_config.endpoint = "http://test-endpoint"
        mock_config.api_key = "test-key"

        mock_session = Mock(spec=Session)
        mock_session.session_id = UUID("00000000-0000-0000-0000-000000000000")
        mock_session.jwt = "test-jwt"
        mock_session.config = mock_config

        # Create a real API client for the session
        mock_session._api = SessionApiClient(
            endpoint=mock_config.endpoint,
            session_id=mock_session.session_id,
            api_key=mock_config.api_key,
            jwt=mock_session.jwt,
        )

        return SessionExporter(session=mock_session)

    def test_event_formatting(self, session_exporter, test_span):
        """Verify events are formatted correctly"""
        with patch.object(session_exporter._api, "create_events", return_value=True) as mock_create:
            result = session_exporter.export([test_span])
            assert result == SpanExportResult.SUCCESS

            # Verify the formatted event
            mock_create.assert_called_once()
            call_args = mock_create.call_args[0]
            events = call_args[0]
            assert len(events) == 1
            event = events[0]
            assert "id" in event
            assert "event_type" in event
            assert "session_id" in event

    def test_retry_logic(self, session_exporter, test_span):
        """Verify retry behavior works as expected"""
        with patch.object(session_exporter._api, "create_events") as mock_create:
            mock_create.side_effect = [False, False, True]

            result = session_exporter.export([test_span])
            assert result == SpanExportResult.SUCCESS
            assert mock_create.call_count == 3

    def test_batch_processing(self, session_exporter, test_span):
        """Verify batch processing works correctly"""
        with patch.object(session_exporter._api, "create_events", return_value=True) as mock_create:
            spans = [test_span for _ in range(5)]
            result = session_exporter.export(spans)
            assert result == SpanExportResult.SUCCESS

            # Verify batch was sent correctly
            mock_create.assert_called_once()
            call_args = mock_create.call_args[0]
            events = call_args[0]
            assert len(events) == 5
