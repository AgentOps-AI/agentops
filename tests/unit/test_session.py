import json
import time
from datetime import datetime, timezone
from typing import Dict, Optional, Sequence
from unittest.mock import MagicMock, Mock, patch
from uuid import UUID

import pytest
import requests_mock
from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExportResult
from opentelemetry.trace import SpanContext, SpanKind, Status, StatusCode
from opentelemetry.trace.span import TraceState

import agentops
from agentops import ActionEvent, Client
from agentops.http_client import HttpClient
from agentops.singleton import clear_singletons


class TestNonInitializedSessions:
    def setup_method(self):
        self.api_key = "11111111-1111-4111-8111-111111111111"
        self.event_type = "test_event_type"

    def test_non_initialized_doesnt_start_session(self, mock_req):
        agentops.set_api_key(self.api_key)
        session = agentops.start_session()
        assert session is None


class TestSingleSessions:
    def setup_method(self):
        self.api_key = "11111111-1111-4111-8111-111111111111"
        self.event_type = "test_event_type"
        agentops.init(api_key=self.api_key, max_wait_time=50, auto_start_session=False)

    def test_session(self, mock_req):
        session = agentops.start_session()

        agentops.record(ActionEvent(self.event_type))
        agentops.record(ActionEvent(self.event_type))

        time.sleep(0.1)
        # 3 Requests: check_for_updates, start_session, create_events (2 in 1)
        assert len(mock_req.request_history) == 3
        time.sleep(0.15)

        assert (
            mock_req.last_request.headers["Authorization"] == f"Bearer {mock_req.session_jwts[str(session.session_id)]}"
        )
        request_json = mock_req.last_request.json()
        assert request_json["events"][0]["event_type"] == self.event_type

        end_state = "Success"
        agentops.end_session(end_state)
        time.sleep(0.15)

        # We should have 4 requests (additional end session)
        assert len(mock_req.request_history) == 4
        assert (
            mock_req.last_request.headers["Authorization"] == f"Bearer {mock_req.session_jwts[str(session.session_id)]}"
        )
        request_json = mock_req.last_request.json()
        assert request_json["session"]["end_state"] == end_state
        assert len(request_json["session"]["tags"]) == 0

        agentops.end_all_sessions()

    def test_add_tags(self, mock_req):
        # Arrange
        tags = ["GPT-4"]
        agentops.start_session(tags=tags)
        agentops.add_tags(["test-tag", "dupe-tag"])
        agentops.add_tags(["dupe-tag"])

        # Act
        end_state = "Success"
        agentops.end_session(end_state)
        time.sleep(0.15)

        # Assert 3 requests, 1 for session init, 1 for event, 1 for end session
        assert mock_req.last_request.headers["X-Agentops-Api-Key"] == self.api_key
        request_json = mock_req.last_request.json()
        assert request_json["session"]["end_state"] == end_state
        assert request_json["session"]["tags"] == ["GPT-4", "test-tag", "dupe-tag"]

        agentops.end_all_sessions()

    def test_tags(self, mock_req):
        # Arrange
        tags = ["GPT-4"]
        agentops.start_session(tags=tags)

        # Act
        agentops.record(ActionEvent(self.event_type))

        # Act
        end_state = "Success"
        agentops.end_session(end_state)
        time.sleep(0.15)

        # 4 requests: check_for_updates, start_session, record_event, end_session
        assert len(mock_req.request_history) == 4
        assert mock_req.last_request.headers["X-Agentops-Api-Key"] == self.api_key
        request_json = mock_req.last_request.json()
        assert request_json["session"]["end_state"] == end_state
        assert request_json["session"]["tags"] == tags

        agentops.end_all_sessions()

    def test_inherit_session_id(self, mock_req):
        # Arrange
        inherited_id = "4f72e834-ff26-4802-ba2d-62e7613446f1"
        agentops.start_session(tags=["test"], inherited_session_id=inherited_id)

        # Act
        # session_id correct
        request_json = mock_req.last_request.json()
        assert request_json["session"]["session_id"] == inherited_id

        # Act
        end_state = "Success"
        agentops.end_session(end_state)
        time.sleep(0.15)

        agentops.end_all_sessions()

    def test_add_tags_with_string(self, mock_req):
        agentops.start_session()
        agentops.add_tags("wrong-type-tags")

        request_json = mock_req.last_request.json()
        assert request_json["session"]["tags"] == ["wrong-type-tags"]

    def test_session_add_tags_with_string(self, mock_req):
        session = agentops.start_session()
        session.add_tags("wrong-type-tags")

        request_json = mock_req.last_request.json()
        assert request_json["session"]["tags"] == ["wrong-type-tags"]

    def test_set_tags_with_string(self, mock_req):
        agentops.start_session()
        agentops.set_tags("wrong-type-tags")

        request_json = mock_req.last_request.json()
        assert request_json["session"]["tags"] == ["wrong-type-tags"]

    def test_session_set_tags_with_string(self, mock_req):
        session = agentops.start_session()
        assert session is not None

        session.set_tags("wrong-type-tags")

        request_json = mock_req.last_request.json()
        assert request_json["session"]["tags"] == ["wrong-type-tags"]

    def test_set_tags_before_session(self, mock_req):
        agentops.configure(default_tags=["pre-session-tag"])
        agentops.start_session()

        request_json = mock_req.last_request.json()
        assert request_json["session"]["tags"] == ["pre-session-tag"]

    def test_safe_get_session_no_session(self, mock_req):
        session = Client()._safe_get_session()
        assert session is None

    def test_safe_get_session_with_session(self, mock_req):
        agentops.start_session()
        session = Client()._safe_get_session()
        assert session is not None

    def test_safe_get_session_with_multiple_sessions(self, mock_req):
        agentops.start_session()
        agentops.start_session()

        session = Client()._safe_get_session()
        assert session is None

    def test_get_analytics(self, mock_req):
        # Arrange
        session = agentops.start_session()
        session.add_tags(["test-session-analytics-tag"])
        assert session is not None

        # Record some events to increment counters
        session.record(ActionEvent("llms"))
        session.record(ActionEvent("tools"))
        session.record(ActionEvent("actions"))
        session.record(ActionEvent("errors"))
        time.sleep(0.1)

        # Act
        analytics = session.get_analytics()

        # Assert
        assert isinstance(analytics, dict)
        assert all(
            key in analytics
            for key in [
                "LLM calls",
                "Tool calls",
                "Actions",
                "Errors",
                "Duration",
                "Cost",
            ]
        )

        # Check specific values
        assert analytics["LLM calls"] == 1
        assert analytics["Tool calls"] == 1
        assert analytics["Actions"] == 1
        assert analytics["Errors"] == 1

        # Check duration format
        assert isinstance(analytics["Duration"], str)
        assert "s" in analytics["Duration"]

        # Check cost format (mock returns token_cost: 5)
        assert analytics["Cost"] == "5.000000"

        # End session and cleanup
        session.end_session(end_state="Success")
        agentops.end_all_sessions()


class TestMultiSessions:
    def setup_method(self):
        self.api_key = "11111111-1111-4111-8111-111111111111"
        self.event_type = "test_event_type"
        agentops.init(api_key=self.api_key, max_wait_time=500, auto_start_session=False)

    def test_two_sessions(self, mock_req):
        session_1 = agentops.start_session()
        session_2 = agentops.start_session()
        assert session_1 is not None
        assert session_2 is not None

        assert len(agentops.Client().current_session_ids) == 2
        assert agentops.Client().current_session_ids == [
            str(session_1.session_id),
            str(session_2.session_id),
        ]
        time.sleep(0.1)

        # Requests: check_for_updates, 2 start_session
        assert len(mock_req.request_history) == 3

        session_1.record(ActionEvent(self.event_type))
        session_2.record(ActionEvent(self.event_type))

        time.sleep(1.5)

        # 5 requests: check_for_updates, 2 start_session, 2 record_event
        assert len(mock_req.request_history) == 5

        # Check the last two requests instead of just the last one
        last_request = mock_req.request_history[-1]
        second_last_request = mock_req.request_history[-2]

        # Verify session_1's request
        assert (
            second_last_request.headers["Authorization"] == f"Bearer {mock_req.session_jwts[str(session_1.session_id)]}"
        )
        assert second_last_request.json()["events"][0]["event_type"] == self.event_type

        # Verify session_2's request
        assert last_request.headers["Authorization"] == f"Bearer {mock_req.session_jwts[str(session_2.session_id)]}"
        assert last_request.json()["events"][0]["event_type"] == self.event_type

        end_state = "Success"

        session_1.end_session(end_state)
        time.sleep(1.5)

        # Additional end session request
        assert len(mock_req.request_history) == 6
        assert (
            mock_req.last_request.headers["Authorization"]
            == f"Bearer {mock_req.session_jwts[str(session_1.session_id)]}"
        )
        request_json = mock_req.last_request.json()
        assert request_json["session"]["end_state"] == end_state
        assert len(request_json["session"]["tags"]) == 0

        session_2.end_session(end_state)
        # Additional end session request
        assert len(mock_req.request_history) == 7
        assert (
            mock_req.last_request.headers["Authorization"]
            == f"Bearer {mock_req.session_jwts[str(session_2.session_id)]}"
        )
        request_json = mock_req.last_request.json()
        assert request_json["session"]["end_state"] == end_state
        assert len(request_json["session"]["tags"]) == 0

    def test_add_tags(self, mock_req):
        # Arrange
        session_1_tags = ["session-1"]
        session_2_tags = ["session-2"]

        session_1 = agentops.start_session(tags=session_1_tags)
        session_2 = agentops.start_session(tags=session_2_tags)
        assert session_1 is not None
        assert session_2 is not None

        session_1.add_tags(["session-1-added", "session-1-added-2"])
        session_2.add_tags(["session-2-added"])

        # Act
        end_state = "Success"
        session_1.end_session(end_state)
        session_2.end_session(end_state)
        time.sleep(0.15)

        # Assert 3 requests, 1 for session init, 1 for event, 1 for end session
        req1 = mock_req.request_history[-1].json()
        req2 = mock_req.request_history[-2].json()

        session_1_req = req1 if req1["session"]["session_id"] == session_1.session_id else req2
        session_2_req = req2 if req2["session"]["session_id"] == session_2.session_id else req1

        assert session_1_req["session"]["end_state"] == end_state
        assert session_2_req["session"]["end_state"] == end_state

        assert session_1_req["session"]["tags"] == [
            "session-1",
            "session-1-added",
            "session-1-added-2",
        ]

        assert session_2_req["session"]["tags"] == [
            "session-2",
            "session-2-added",
        ]

    def test_get_analytics_multiple_sessions(self, mock_req):
        session_1 = agentops.start_session()
        session_1.add_tags(["session-1", "test-analytics-tag"])
        session_2 = agentops.start_session()
        session_2.add_tags(["session-2", "test-analytics-tag"])
        assert session_1 is not None
        assert session_2 is not None

        # Record events in the sessions
        session_1.record(ActionEvent("llms"))
        session_1.record(ActionEvent("tools"))
        session_2.record(ActionEvent("actions"))
        session_2.record(ActionEvent("errors"))

        time.sleep(1.5)

        # Act
        analytics_1 = session_1.get_analytics()
        analytics_2 = session_2.get_analytics()

        # Assert 2 record_event requests - 2 for each session
        assert analytics_1["LLM calls"] == 1
        assert analytics_1["Tool calls"] == 1
        assert analytics_1["Actions"] == 0
        assert analytics_1["Errors"] == 0

        assert analytics_2["LLM calls"] == 0
        assert analytics_2["Tool calls"] == 0
        assert analytics_2["Actions"] == 1
        assert analytics_2["Errors"] == 1

        # Check duration format
        assert isinstance(analytics_1["Duration"], str)
        assert "s" in analytics_1["Duration"]
        assert isinstance(analytics_2["Duration"], str)
        assert "s" in analytics_2["Duration"]

        # Check cost format (mock returns token_cost: 5)
        assert analytics_1["Cost"] == "5.000000"
        assert analytics_2["Cost"] == "5.000000"

        end_state = "Success"

        session_1.end_session(end_state)
        session_2.end_session(end_state)


class TestSessionExporter:
    def setup_method(self):
        self.api_key = "11111111-1111-4111-8111-111111111111"
        # Initialize agentops first
        agentops.init(api_key=self.api_key, max_wait_time=50, auto_start_session=False)
        self.session = agentops.start_session()
        assert self.session is not None  # Verify session was created
        self.exporter = self.session._otel_exporter

    def teardown_method(self):
        """Clean up after each test"""
        if self.session:
            self.session.end_session("Success")
        agentops.end_all_sessions()
        clear_singletons()

    def create_test_span(self, name="test_span", attributes=None):
        """Helper to create a test span with required attributes"""
        if attributes is None:
            attributes = {}

        # Ensure required attributes are present
        base_attributes = {
            "event.id": str(UUID(int=1)),
            "event.type": "test_type",
            "event.timestamp": datetime.now(timezone.utc).isoformat(),
            "event.end_timestamp": datetime.now(timezone.utc).isoformat(),
            "event.data": json.dumps({"test": "data"}),
            "session.id": str(self.session.session_id),
        }
        base_attributes.update(attributes)

        context = SpanContext(
            trace_id=0x000000000000000000000000DEADBEEF,
            span_id=0x00000000DEADBEF0,
            is_remote=False,
            trace_state=TraceState(),
        )

        return ReadableSpan(
            name=name,
            context=context,
            kind=SpanKind.INTERNAL,
            status=Status(StatusCode.OK),
            start_time=123,
            end_time=456,
            attributes=base_attributes,
            events=[],
            links=[],
            resource=self.session._tracer_provider.resource,
        )

    def test_export_basic_span(self, mock_req):
        """Test basic span export with all required fields"""
        span = self.create_test_span()
        result = self.exporter.export([span])

        assert result == SpanExportResult.SUCCESS
        assert len(mock_req.request_history) > 0

        last_request = mock_req.last_request.json()
        assert "events" in last_request
        event = last_request["events"][0]

        # Verify required fields
        assert "id" in event
        assert "event_type" in event
        assert "init_timestamp" in event
        assert "end_timestamp" in event
        assert "session_id" in event

    def test_export_action_event(self, mock_req):
        """Test export of action event with specific formatting"""
        action_attributes = {
            "event.data": json.dumps(
                {
                    "action_type": "test_action",
                    "params": {"param1": "value1"},
                    "returns": "test_return",
                }
            )
        }

        span = self.create_test_span(name="actions", attributes=action_attributes)
        result = self.exporter.export([span])

        assert result == SpanExportResult.SUCCESS

        last_request = mock_req.request_history[-1].json()
        event = last_request["events"][0]

        assert event["action_type"] == "test_action"
        assert event["params"] == {"param1": "value1"}
        assert event["returns"] == "test_return"

    def test_export_tool_event(self, mock_req):
        """Test export of tool event with specific formatting"""
        tool_attributes = {
            "event.data": json.dumps(
                {
                    "name": "test_tool",
                    "params": {"param1": "value1"},
                    "returns": "test_return",
                }
            )
        }

        span = self.create_test_span(name="tools", attributes=tool_attributes)
        result = self.exporter.export([span])

        assert result == SpanExportResult.SUCCESS

        last_request = mock_req.request_history[-1].json()
        event = last_request["events"][0]

        assert event["name"] == "test_tool"
        assert event["params"] == {"param1": "value1"}
        assert event["returns"] == "test_return"

    def test_export_with_missing_timestamp(self, mock_req):
        """Test handling of missing end_timestamp"""
        attributes = {"event.end_timestamp": None}  # This should be handled gracefully

        span = self.create_test_span(attributes=attributes)
        result = self.exporter.export([span])

        assert result == SpanExportResult.SUCCESS

        last_request = mock_req.request_history[-1].json()
        event = last_request["events"][0]

        # Verify end_timestamp is present and valid
        assert "end_timestamp" in event
        assert event["end_timestamp"] is not None

    def test_export_with_missing_timestamps_advanced(self, mock_req):
        """Test handling of missing timestamps"""
        attributes = {"event.timestamp": None, "event.end_timestamp": None}

        span = self.create_test_span(attributes=attributes)
        result = self.exporter.export([span])

        assert result == SpanExportResult.SUCCESS

        last_request = mock_req.request_history[-1].json()
        event = last_request["events"][0]

        # Verify timestamps are present and valid
        assert "init_timestamp" in event
        assert "end_timestamp" in event
        assert event["init_timestamp"] is not None
        assert event["end_timestamp"] is not None

        # Verify timestamps are in ISO format
        try:
            datetime.fromisoformat(event["init_timestamp"].replace("Z", "+00:00"))
            datetime.fromisoformat(event["end_timestamp"].replace("Z", "+00:00"))
        except ValueError:
            pytest.fail("Timestamps are not in valid ISO format")

    def test_export_with_shutdown(self, mock_req):
        """Test export behavior when shutdown"""
        self.exporter._shutdown.set()
        span = self.create_test_span()

        result = self.exporter.export([span])
        assert result == SpanExportResult.SUCCESS

        # Verify no request was made
        assert not any(req.url.endswith("/v2/create_events") for req in mock_req.request_history[-1:])

    def test_export_llm_event(self, mock_req):
        """Test export of LLM event with specific handling of timestamps"""
        llm_attributes = {
            "event.data": json.dumps(
                {
                    "prompt": "test prompt",
                    "completion": "test completion",
                    "model": "test-model",
                    "tokens": 100,
                    "cost": 0.002,
                }
            )
        }

        span = self.create_test_span(name="llms", attributes=llm_attributes)
        result = self.exporter.export([span])

        assert result == SpanExportResult.SUCCESS

        last_request = mock_req.request_history[-1].json()
        event = last_request["events"][0]

        # Verify LLM specific fields
        assert event["prompt"] == "test prompt"
        assert event["completion"] == "test completion"
        assert event["model"] == "test-model"
        assert event["tokens"] == 100
        assert event["cost"] == 0.002

        # Verify timestamps
        assert event["init_timestamp"] is not None
        assert event["end_timestamp"] is not None

    def test_export_with_missing_id(self, mock_req):
        """Test handling of missing event ID"""
        attributes = {"event.id": None}

        span = self.create_test_span(attributes=attributes)
        result = self.exporter.export([span])

        assert result == SpanExportResult.SUCCESS

        last_request = mock_req.request_history[-1].json()
        event = last_request["events"][0]

        # Verify ID is present and valid UUID
        assert "id" in event
        assert event["id"] is not None
        try:
            UUID(event["id"])
        except ValueError:
            pytest.fail("Event ID is not a valid UUID")
