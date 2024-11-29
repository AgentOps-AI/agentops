import json
import time  # Add to existing imports
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExportResult
from opentelemetry.trace import SpanKind

from agentops.config import Configuration
from agentops.event import ActionEvent, ErrorEvent, Event
from agentops.session import Session
from agentops.session.exporter import SessionExporter


@pytest.fixture
def exporter(session):
    """Create a SessionExporter instance for testing"""
    return SessionExporter(session=session)


def test_exporter_initialization(session):
    """Test that SessionExporter initializes correctly"""
    exporter = SessionExporter(session)
    assert exporter.session == session
    assert not exporter._shutdown.is_set()


def test_generic_adapter_conversion(session):
    """Test GenericAdapter's conversion of attributes to and from span attributes"""
    from datetime import datetime
    from uuid import UUID

    from agentops.event import ActionEvent
    from agentops.session.exporter import SessionSpanAdapter

    # Create a test event with various attribute types
    test_event = ActionEvent(
        action_type="test_action",
        params={
            "str_attr": "test_string",
            "int_attr": 42,
            "float_attr": 3.14,
            "bool_attr": True,
            "datetime_attr": datetime(2024, 1, 1),
            "uuid_attr": UUID("12345678-1234-5678-1234-567812345678"),
            "dict_attr": {"key": "value"},
        },
    )
    test_event.session_id = session.session_id

    # Test conversion to span attributes
    span_attrs = SessionSpanAdapter.to_span_attributes(test_event)

    # Verify basic attribute conversion
    assert span_attrs["event.type"] == "actions"
    assert span_attrs["event.action_type"] == "test_action"

    # Verify params are properly serialized
    assert "event.params" in span_attrs
    params = (
        json.loads(span_attrs["event.params"])
        if isinstance(span_attrs["event.params"], str)
        else span_attrs["event.params"]
    )
    assert params["str_attr"] == "test_string"
    assert params["int_attr"] == 42
    assert params["float_attr"] == 3.14
    assert params["bool_attr"] is True
    assert "2024-01-01" in str(params["datetime_attr"])
    assert "12345678-1234-5678-1234-567812345678" in str(params["uuid_attr"])
    assert params["dict_attr"] == {"key": "value"}

    # Verify session ID handling
    assert span_attrs["session.id"] == str(session.session_id)

    # Test conversion back from span attributes
    event_attrs = SessionSpanAdapter.from_span_attributes(span_attrs)

    # Verify event structure
    assert event_attrs["event_type"] == "actions"
    assert event_attrs["action_type"] == "test_action"
    assert isinstance(event_attrs["params"], dict)


def test_export_empty_spans(session):
    """Test exporting empty spans list"""
    result = session._exporter.export([])
    assert result == SpanExportResult.SUCCESS


def test_export_spans(mocker, session):
    """Test exporting spans with event data"""
    # Create spy on session.api.batch
    batch_spy = mocker.spy(session.api, "batch")

    # Create a mock span for an action event
    span = Mock(spec=ReadableSpan)
    span.name = "actions"  # This should be "actions" for action events
    span.attributes = {
        "event.id": "123",
        "event.type": "actions",  # Event type should match span name
        "event.action_type": "test_action",  # The actual action name goes here
        "event.timestamp": "2024-01-01T00:00:00Z",
        "event.end_timestamp": "2024-01-01T00:00:01Z",
        "event.data": '{"key": "value"}',
        "session.id": str(session.session_id),
    }

    # Export the span using session's exporter
    result = session._exporter.export([span])

    # Verify the export
    assert result == SpanExportResult.SUCCESS
    batch_spy.assert_called_once()

    # Verify the event data format
    call_args = batch_spy.call_args[0][0]  # Get first positional arg of first call
    assert len(call_args) == 1
    event_data = call_args[0]
    assert event_data["event_type"] == "actions"  # Should be "actions" for action events
    assert event_data["session_id"] == str(session.session_id)


def test_export_with_shutdown(session):
    """Test that export returns success when shutdown"""
    session._exporter._shutdown.set()
    result = session._exporter.export([Mock(spec=ReadableSpan)])
    assert result == SpanExportResult.SUCCESS


def test_force_flush(session):
    """Test force_flush functionality"""
    assert session._exporter.force_flush() is True


def test_shutdown(session):
    """Test shutdown functionality"""
    session._exporter.shutdown()
    assert session._exporter._shutdown.is_set()


@pytest.mark.asyncio
async def test_async_export(session):
    """Test exporting spans asynchronously"""
    span = Mock(spec=ReadableSpan)
    span.name = "async_test"
    span.attributes = {
        "event.id": "456",
        "event.type": "async_test",
        "event.timestamp": "2024-01-01T00:00:00Z",
        "event.end_timestamp": "2024-01-01T00:00:01Z",
        "event.data": '{"async": true}',
        "session.id": str(session.session_id),
    }

    result = session._exporter.export([span])
    assert result == SpanExportResult.SUCCESS


def test_export_error_handling(mocker, session):
    """Test error handling during export"""
    # Mock the batch method to raise an exception
    mocker.patch.object(session.api, "batch", side_effect=Exception("Test error"))

    span = Mock(spec=ReadableSpan)
    span.name = "error_test"
    span.attributes = {"evmestamp": "BAD DATA"}

    result = session._exporter.export([span])
    assert result == SpanExportResult.FAILURE


def test_span_processor_config(session):
    """Test that BatchSpanProcessor is configured correctly for testing"""
    # Verify the processor exists and is configured
    assert hasattr(session, "_span_processor")
    assert session._span_processor is not None


def test_event_recording(session, mock_req):
    """Test recording a single event"""
    event = ActionEvent("test_action")
    session.record(event, flush_now=True)

    create_events_requests = [req for req in mock_req.request_history if req.url.endswith("/v2/create_events")]
    assert len(create_events_requests) > 0

    events = create_events_requests[-1].json()["events"]
    assert len(events) == 1
    assert events[0]["event_type"] == "test_action"  # Type should be "actions"


def test_multiple_event_types(session, mock_req):
    """Test recording different types of events"""
    session.record(ActionEvent("test_action2"), flush_now=True)

    create_events_requests = [req for req in mock_req.request_history if req.url.endswith("/v2/create_events")]
    assert len(create_events_requests) > 0

    events = create_events_requests[-1].json()["events"]
    assert len(events) == 1
    assert events[0]["event_type"] == "test_action2"


def test_session_cleanup(mocker, session, mock_req):
    """Test that session cleanup works properly"""
    # Mock the update_session method
    update_mock = mocker.patch.object(
        session.api, "update_session", return_value=({"session": {"end_state": "Success"}}, None)
    )

    # Record an event
    event = ActionEvent("test_cleanup")
    session.record(event, flush_now=True)

    # End session
    session.end_session("Success")

    # Verify update_session was called
    update_mock.assert_called()

    # Verify session end state
    assert session.end_state == "Success"


def test_event_export_through_processor(session):
    """Test that events are properly exported through the span processor"""
    # Create a mock for the export method
    with patch("agentops.session.exporter.SessionExporter.export") as mock_export:
        # Set up mock return value
        mock_export.return_value = SpanExportResult.SUCCESS

        # Create and record an event
        event = ActionEvent("test_action")
        session.record(event)

        # Force flush to ensure export happens
        session._span_processor.force_flush()

        # Verify exporter was called
        assert mock_export.call_count > 0

        # Get the exported spans
        exported_spans = mock_export.call_args[0][0]
        assert len(exported_spans) > 0

        # Verify span attributes
        exported_span = exported_spans[0]
        assert exported_span.name == "test_action"
        assert "event.type" in exported_span.attributes
