import json
import time
from typing import Dict, Optional, Sequence
from unittest.mock import MagicMock, Mock, patch
from datetime import datetime, timezone

import pytest
import requests_mock
from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.trace import SpanContext, SpanKind
from opentelemetry.sdk.trace.export import SpanExportResult
from opentelemetry.trace import Status, StatusCode
from opentelemetry.trace.span import TraceState
from uuid import UUID

import agentops
from agentops import ActionEvent, Client
from agentops.http_client import HttpClient
from agentops.singleton import clear_singletons
import asyncio


@pytest.fixture(autouse=True)
def setup_teardown(mock_req):
    clear_singletons()
    yield
    agentops.end_all_sessions()  # teardown part


@pytest.fixture(autouse=True, scope="function")
def mock_req():
    with requests_mock.Mocker() as m:
        url = "https://api.agentops.ai"
        m.post(url + "/v2/create_events", json={"status": "ok"})
        m.post(url + "/v2/create_session", json={"status": "success", "jwt": "some_jwt"})
        m.post(url + "/v2/reauthorize_jwt", json={"status": "success", "jwt": "some_jwt"})
        m.post(url + "/v2/update_session", json={"status": "success", "token_cost": 5})
        m.post(url + "/v2/developer_errors", json={"status": "ok"})
        m.post("https://pypi.org/pypi/agentops/json", status_code=404)
        yield m


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
        agentops.start_session()

        agentops.record(ActionEvent(self.event_type))
        agentops.record(ActionEvent(self.event_type))

        time.sleep(0.1)
        # 3 Requests: check_for_updates, start_session, create_events (2 in 1)
        assert len(mock_req.request_history) == 3
        time.sleep(0.15)

        assert mock_req.last_request.headers["Authorization"] == "Bearer some_jwt"
        request_json = mock_req.last_request.json()
        assert request_json["events"][0]["event_type"] == self.event_type

        end_state = "Success"
        agentops.end_session(end_state)
        time.sleep(0.15)

        # We should have 4 requests (additional end session)
        assert len(mock_req.request_history) == 4
        assert mock_req.last_request.headers["Authorization"] == "Bearer some_jwt"
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
        assert mock_req.last_request.headers["Authorization"] == "Bearer some_jwt"
        request_json = mock_req.last_request.json()
        assert request_json["events"][0]["event_type"] == self.event_type

        end_state = "Success"

        session_1.end_session(end_state)
        time.sleep(1.5)

        # Additional end session request
        assert len(mock_req.request_history) == 6
        assert mock_req.last_request.headers["Authorization"] == "Bearer some_jwt"
        request_json = mock_req.last_request.json()
        assert request_json["session"]["end_state"] == end_state
        assert len(request_json["session"]["tags"]) == 0

        session_2.end_session(end_state)
        # Additional end session request
        assert len(mock_req.request_history) == 7
        assert mock_req.last_request.headers["Authorization"] == "Bearer some_jwt"
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
        """Set up test method."""
        clear_singletons()  # Clear any existing singletons first
        import agentops

        self.api_key = "11111111-1111-4111-8111-111111111111"
        self.agentops = agentops
        self.agentops.init(api_key=self.api_key, max_wait_time=50, auto_start_session=False)
        self.session = self.agentops.start_session()
        assert self.session is not None
        self.exporter = self.session._otel_exporter
        self.test_span = self.create_test_span()

    def teardown_method(self):
        """Clean up after test method."""
        if hasattr(self, "session"):
            self.session.end_session()
        self.agentops.end_all_sessions()
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

    @pytest.mark.asyncio
    async def test_export_basic_span(self, setup_test_session, mock_req):
        """Test basic span export with all required fields"""
        span = await self.create_test_span()
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

    @pytest.mark.asyncio
    async def test_export_action_event(self, setup_test_session, mock_req):
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

        span = await self.create_test_span(name="actions", attributes=action_attributes)
        result = self.exporter.export([span])

        assert result == SpanExportResult.SUCCESS

        last_request = mock_req.request_history[-1].json()
        event = last_request["events"][0]

        assert event["action_type"] == "test_action"
        assert event["params"] == {"param1": "value1"}
        assert event["returns"] == "test_return"

    @pytest.mark.asyncio
    async def test_export_tool_event(self, setup_test_session, mock_req):
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

        span = await self.create_test_span(name="tools", attributes=tool_attributes)
        result = self.exporter.export([span])

        assert result == SpanExportResult.SUCCESS

        last_request = mock_req.request_history[-1].json()
        event = last_request["events"][0]

        assert event["name"] == "test_tool"
        assert event["params"] == {"param1": "value1"}
        assert event["returns"] == "test_return"

    @pytest.mark.asyncio
    async def test_export_with_missing_timestamp(self, setup_test_session, mock_req):
        """Test handling of missing end_timestamp"""
        attributes = {"event.end_timestamp": None}  # This should be handled gracefully

        span = await self.create_test_span(attributes=attributes)
        result = self.exporter.export([span])

        assert result == SpanExportResult.SUCCESS

        last_request = mock_req.request_history[-1].json()
        event = last_request["events"][0]

        # Verify end_timestamp is present and valid
        assert "end_timestamp" in event
        assert event["end_timestamp"] is not None

    @pytest.mark.asyncio
    async def test_export_with_missing_timestamps_advanced(self, setup_test_session, mock_req):
        """Test handling of missing timestamps"""
        attributes = {"event.timestamp": None, "event.end_timestamp": None}

        span = await self.create_test_span(attributes=attributes)
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

    @pytest.mark.asyncio
    async def test_export_with_shutdown(self, setup_test_session, mock_req):
        """Test export behavior when shutdown"""
        self.exporter._shutdown.set()
        span = await self.create_test_span()

        result = self.exporter.export([span])
        assert result == SpanExportResult.SUCCESS

        # Verify no request was made
        assert not any(req.url.endswith("/v2/create_events") for req in mock_req.request_history[-1:])

    @pytest.mark.asyncio
    async def test_export_llm_event(self, setup_teardown, mock_req):
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

        span = await self.create_test_span(name="llms", attributes=llm_attributes)
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

    @pytest.mark.asyncio
    async def test_voyage_provider(self):
        """Test the VoyageProvider class with event data verification."""
        try:
            import voyageai
        except ImportError:
            pytest.skip("voyageai package not installed")

        from agentops.llms.providers.voyage import VoyageProvider
        from agentops.session import Session
        from agentops.config import Configuration
        from agentops.event import LLMEvent, EventType
        from uuid import uuid4
        import json
        import requests_mock

        # Test implementation with mock clients
        class MockVoyageClient:
            def __init__(self):
                self.warnings = []
                self.events = []

            def record(self, event):
                """Mock record method required by InstrumentedProvider."""
                self.events.append(event)

            def add_pre_init_warning(self, message):
                """Mock method to handle configuration warnings."""
                self.warnings.append(message)

            def embed(self, input_text, **kwargs):
                """Mock embed method matching Voyage API interface."""
                return {
                    "data": [{"embedding": [0.1] * 1024}],  # Test data format
                    "embeddings": [[0.2] * 1024],  # Test embeddings format
                    "usage": {"prompt_tokens": 10, "completion_tokens": 0},
                    "model": "voyage-01",
                }

            async def aembed(self, input_text, **kwargs):
                """Mock async embed method."""
                return self.embed(input_text, **kwargs)

        # Mock API responses
        with requests_mock.Mocker() as m:
            m.post("https://api.agentops.ai/v2/create_session", json={"status": "success"})
            m.post("https://api.agentops.ai/v2/create_agent", json={"status": "success"})
            m.post("https://api.agentops.ai/v2/event", json={"status": "success"})
            m.post("https://api.agentops.ai/v2/shutdown_session", json={"status": "success"})
            m.post("https://api.agentops.ai/v2/session_stats", json={"status": "success"})

            mock_client = MockVoyageClient()
            provider = VoyageProvider(client=mock_client)
            provider.override()

            # Test sync embedding with event data verification
            config = Configuration()
            config.configure(mock_client, api_key=str(uuid4()))
            session = Session(session_id=uuid4(), config=config)
            test_input = "test input"

            # Create agent for session with required parameters
            agent_name = "Test Agent"
            agent_id = str(uuid4())
            session.create_agent(name=agent_name, agent_id=agent_id)

            # Create and record LLM event for sync embedding
            result = provider.embed(test_input, session=session)
            event = LLMEvent(
                prompt=test_input,
                completion={"type": "embedding", "vector": result["embeddings"][0]},
                prompt_tokens=result["usage"]["prompt_tokens"],
                completion_tokens=0,
                model=result["model"],
                params={"input_text": test_input},
                returns=result,
                agent_id=agent_id,
            )
            session.record(event)

            # Verify basic response
            assert isinstance(result, dict)
            assert "embeddings" in result
            assert isinstance(result["embeddings"], list)
            assert len(result["embeddings"]) == 1
            assert len(result["embeddings"][0]) == 1024

            # Verify event data format
            assert event.event_type == EventType.LLM.value
            assert event.model == "voyage-01"
            assert event.prompt == test_input
            assert isinstance(event.completion, dict)
            assert event.completion["type"] == "embedding"
            assert isinstance(event.completion["vector"], list)
            assert len(event.completion["vector"]) == 1024
            assert event.params == {"input_text": test_input}
            assert isinstance(event.returns, dict)
            assert "data" in event.returns
            assert "embeddings" in event.returns
            assert "usage" in event.returns
            assert "model" in event.returns
            # Verify usage information
            assert "usage" in result
            assert "prompt_tokens" in result["usage"]
            assert result["usage"]["prompt_tokens"] == 10
            assert "completion_tokens" in result["usage"]
            assert result["usage"]["completion_tokens"] == 0

            # Verify model information
            assert "model" in result
            assert result["model"] == "voyage-01"

            # Test async embedding with event data verification
            session = Session(session_id=uuid4(), config=config)  # Fresh session for async test
            agent_name = "Test Agent Async"
            agent_id = str(uuid4())
            session.create_agent(name=agent_name, agent_id=agent_id)  # Create agent for async test
            result = await provider.aembed(test_input, session=session)

            # Create and record LLM event for async embedding
            event = LLMEvent(
                prompt=test_input,
                completion={"type": "embedding", "vector": result["embeddings"][0]},
                prompt_tokens=result["usage"]["prompt_tokens"],
                completion_tokens=0,
                model=result["model"],
                params={"input_text": test_input},
                returns=result,
                agent_id=agent_id,
            )
            session.record(event)

            # Print event data for verification

            # Verify basic response
            assert isinstance(result, dict)
            assert "embeddings" in result
            assert isinstance(result["embeddings"], list)
            assert len(result["embeddings"]) == 1
            assert len(result["embeddings"][0]) == 1024
            # Verify event data format
            assert event.event_type == EventType.LLM.value
            assert event.model == "voyage-01"
            assert event.prompt == test_input
            assert isinstance(event.completion, dict)
            assert event.completion["type"] == "embedding"
            assert isinstance(event.completion["vector"], list)
            assert len(event.completion["vector"]) == 1024
            assert event.params == {"input_text": test_input}
            assert isinstance(event.returns, dict)
            assert "data" in event.returns
            assert "embeddings" in event.returns
            assert "usage" in event.returns
            assert "model" in event.returns
            # Verify usage information
            assert "usage" in result
            assert "prompt_tokens" in result["usage"]
            assert result["usage"]["prompt_tokens"] == 10
            assert "completion_tokens" in result["usage"]
            assert result["usage"]["completion_tokens"] == 0

            # Verify model information
            assert "model" in result
            assert result["model"] == "voyage-01"

            # Test error handling
            class ErrorClient:
                """Client that raises errors for testing error handling."""

                def record(self, *args, **kwargs):
                    raise ValueError("Test error")

                def embed(self, input_text: str, **kwargs):
                    """Raise error for sync embedding."""
                    raise ValueError("Test embedding error")

                async def aembed(self, input_text: str, **kwargs):
                    """Raise error for async embedding."""
                    raise ValueError("Test async embedding error")

            error_client = ErrorClient()
            error_provider = VoyageProvider(client=error_client)
            error_provider.override()

            # Test sync error
            with pytest.raises(Exception):
                error_provider.embed("test input")

            # Test async error
            with pytest.raises(Exception):
                await error_provider.aembed("test input")

    @pytest.mark.asyncio
    async def test_voyage_provider_error_handling(self):
        """Test VoyageProvider error handling for both sync and async methods."""
        from agentops.llms.providers.voyage import VoyageProvider
        from agentops.event import ErrorEvent

        # Initialize provider with error client
        error_client = self.ErrorClient()
        provider = VoyageProvider(client=error_client)
        session = self.client.initialize()

        # Test sync error handling
        with pytest.raises(ValueError, match="Test embedding error"):
            provider.embed("test text", session=session)

        # Verify error event was recorded
        events = session.get_events()
        assert len(events) == 1
        assert isinstance(events[0], ErrorEvent)
        assert "Test embedding error" in str(events[0].exception)

        # Test async error handling
        with pytest.raises(ValueError, match="Test async embedding error"):
            await provider.aembed("test text", session=session)

        # Verify error event was recorded
        events = session.get_events()
        assert len(events) == 2
        assert isinstance(events[1], ErrorEvent)
        assert "Test async embedding error" in str(events[1].exception)

        # Clean up
        self.client.end_session("Error", "Test completed with expected errors")

    @pytest.mark.asyncio
    async def test_voyage_provider_python_version_warning(self):
        """Test Python version warning for Voyage AI provider."""
        import warnings
        from agentops.llms.providers.voyage import VoyageProvider

        # Mock Python version to 3.7
        with patch("sys.version_info", (3, 7)):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")  # Enable all warnings
                VoyageProvider()
                assert len(w) == 1
                assert "requires Python >=3.9" in str(w[0].message)
                assert isinstance(w[0].message, UserWarning)  # Verify warning type

        # Test with Python 3.9 (no warning)
        with patch("sys.version_info", (3, 9)):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                VoyageProvider()
                assert len(w) == 0  # No warning should be raised
