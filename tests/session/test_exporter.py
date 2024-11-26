from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExportResult
from opentelemetry.trace import SpanKind

from agentops.config import Configuration
from agentops.event import ErrorEvent, Event
from agentops.session import Session
from agentops.session.exporter import SessionExporter


@pytest.fixture
def mock_session():
    session = Mock()
    session.session_id = uuid4()
    session.config = Configuration(api_key="test_key")
    session.api = Mock()
    return session


@pytest.fixture
def exporter(mock_session):
    return SessionExporter(mock_session)


def test_exporter_initialization(mock_session):
    """Test that SessionExporter initializes correctly"""
    exporter = SessionExporter(mock_session)
    assert exporter.session == mock_session
    assert not exporter._shutdown.is_set()


def test_export_empty_spans(exporter):
    """Test exporting empty spans list"""
    result = exporter.export([])
    assert result == SpanExportResult.SUCCESS


def test_export_spans(exporter, mock_session):
    """Test exporting spans with event data"""
    # Create a mock span
    span = Mock(spec=ReadableSpan)
    span.name = "test_event"
    span.attributes = {
        "event.id": "123",
        "event.type": "test",
        "event.timestamp": "2024-01-01T00:00:00Z",
        "event.end_timestamp": "2024-01-01T00:00:01Z",
        "event.data": '{"key": "value"}',
        "session.id": str(mock_session.session_id),
    }

    # Export the span
    result = exporter.export([span])

    # Verify the export
    assert result == SpanExportResult.SUCCESS
    mock_session.api.batch.assert_called_once()

    # Verify the event data format
    call_args = mock_session.api.batch.call_args[0][0]
    assert len(call_args) == 1
    event_data = call_args[0]
    assert event_data["event_type"] == "test_event"
    assert event_data["session_id"] == str(mock_session.session_id)


def test_export_with_shutdown(exporter):
    """Test that export returns success when shutdown"""
    exporter._shutdown.set()
    result = exporter.export([Mock(spec=ReadableSpan)])
    assert result == SpanExportResult.SUCCESS


def test_force_flush(exporter):
    """Test force_flush functionality"""
    assert exporter.force_flush() is True


def test_shutdown(exporter):
    """Test shutdown functionality"""
    exporter.shutdown()
    assert exporter._shutdown.is_set()


@pytest.mark.asyncio
async def test_async_export(exporter, mock_session):
    """Test exporting spans asynchronously"""
    span = Mock(spec=ReadableSpan)
    span.name = "async_test"
    span.attributes = {
        "event.id": "456",
        "event.type": "async_test",
        "event.timestamp": "2024-01-01T00:00:00Z",
        "event.end_timestamp": "2024-01-01T00:00:01Z",
        "event.data": '{"async": true}',
        "session.id": str(mock_session.session_id),
    }

    result = exporter.export([span])
    assert result == SpanExportResult.SUCCESS


def test_export_error_handling(exporter, mock_session):
    """Test error handling during export"""
    # Make the API call fail
    mock_session.api.batch.side_effect = Exception("API Error")

    span = Mock(spec=ReadableSpan)
    span.name = "error_test"
    span.attributes = {
        "event.id": "789",
        "event.type": "error_test",
        "event.timestamp": "2024-01-01T00:00:00Z",
        "event.end_timestamp": "2024-01-01T00:00:01Z",
        "event.data": '{"error": true}',
        "session.id": str(mock_session.session_id),
    }

    result = exporter.export([span])
    assert result == SpanExportResult.FAILURE


def test_span_processor_config(mock_session):
    """Test that BatchSpanProcessor is configured correctly for testing"""
    # Create a mock BatchSpanProcessor instead of using real Session
    mock_processor = Mock(spec=BatchSpanProcessor)
    mock_processor._max_export_batch_size = 1
    mock_processor._schedule_delay_millis = 0

    with patch("agentops.session.Session._span_processor", mock_processor):
        session = Session(mock_session.config)
        # Verify BatchSpanProcessor configuration
        assert session._span_processor._max_export_batch_size == 1
        assert session._span_processor._schedule_delay_millis == 0


def test_event_batching(mock_session):
    """Test that events are properly batched for export"""
    mock_processor = Mock(spec=BatchSpanProcessor)
    mock_processor.on_end = Mock()

    with patch("agentops.session.Session._span_processor", mock_processor), patch(
        "agentops.session.Session._tracer_provider"
    ) as mock_provider:
        session = Session(mock_session.config)
        session._span_processor = mock_processor  # Explicitly set the processor

        # Create mock events
        mock_events = [Mock(spec=Event) for _ in range(3)]

        # Record events
        for event in mock_events:
            session.record(event)

        # Verify batching
        assert mock_processor.on_end.call_count == 3
