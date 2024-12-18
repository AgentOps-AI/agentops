import pytest
import requests_mock
import time
import agentops
from agentops import record_action
from datetime import datetime
from agentops.singleton import clear_singletons
import contextlib
from agentops.http_client import HttpClient

jwts = ["some_jwt", "some_jwt2", "some_jwt3"]


@pytest.fixture(autouse=True)
def setup_teardown():
    clear_singletons()
    HttpClient.set_base_url("")  # Reset base URL for testing
    yield
    agentops.end_all_sessions()  # teardown part


@pytest.fixture(autouse=True, scope="function")
def mock_req():
    """Set up mock requests."""
    with requests_mock.Mocker() as m:
        base_url = "http://localhost"  # Use localhost for test mode without /v2 prefix
        api_key = "2a458d3f-5bd7-4798-b862-7d9a54515689"
        jwts = ["some_jwt", "some_jwt2", "some_jwt3"]
        session_counter = {"count": 0}

        def match_headers(request):
            headers = {k.lower(): v for k, v in request.headers.items()}
            return headers.get("x-agentops-api-key") == api_key and (
                headers.get("authorization", "").startswith("Bearer ") or request.path == "/v2/sessions/start"
            )

        def get_next_jwt(request):
            if request.path == "/v2/sessions/start":
                jwt = jwts[session_counter["count"] % len(jwts)]
                session_counter["count"] += 1
                return jwt
            return jwts[0]

        # Mock v2 endpoints with consistent paths and response format
        m.post(
            f"{base_url}/v2/sessions/start",
            json=lambda request, context: {
                "success": True,
                "jwt": get_next_jwt(request),
                "session_id": "test-session-id",
                "session_url": "https://app.agentops.ai/session/123",
            },
            additional_matcher=match_headers,
        )
        m.post(f"{base_url}/v2/sessions/test-session-id/events", json={"success": True}, additional_matcher=match_headers)
        m.post(
            f"{base_url}/v2/sessions/test-session-id/jwt",
            json={"success": True, "jwt": "test-jwt-token"},
            additional_matcher=match_headers,
        )
        m.post(
            f"{base_url}/v2/sessions/test-session-id/update",
            json={"success": True, "token_cost": 5},
            additional_matcher=match_headers,
        )
        m.post(f"{base_url}/v2/sessions/test-session-id/end", json={"success": True}, additional_matcher=match_headers)

        yield m


class TestRecordAction:
    def setup_method(self):
        """Set up test environment"""
        clear_singletons()  # Reset singleton state
        agentops.end_all_sessions()  # Ensure clean state
        HttpClient.set_base_url("")  # Reset base URL for testing
        self.api_key = "2a458d3f-5bd7-4798-b862-7d9a54515689"
        agentops.init(self.api_key, auto_start_session=False)  # Initialize with API key
        self.event_type = "test_event_type"

    def test_record_action_decorator(self, mock_req):
        agentops.start_session()

        @record_action(event_name=self.event_type)
        def add_two(x, y):
            return x + y

        # Act
        add_two(3, 4)
        time.sleep(0.1)

        # 3 requests: check_for_updates, start_session, record_action
        assert len(mock_req.request_history) == 3
        assert mock_req.last_request.headers["X-Agentops-Api-Key"] == self.api_key
        request_json = mock_req.last_request.json()
        assert request_json["events"][0]["action_type"] == self.event_type
        assert request_json["events"][0]["params"] == {"x": 3, "y": 4}
        assert request_json["events"][0]["returns"] == 7

        agentops.end_session(end_state="Success")

    def test_record_action_default_name(self, mock_req):
        agentops.start_session()

        @record_action()
        def add_two(x, y):
            return x + y

        # Act
        add_two(3, 4)
        time.sleep(0.1)

        # 3 requests: check_for_updates, start_session, record_action
        assert len(mock_req.request_history) == 3
        assert mock_req.last_request.headers["X-Agentops-Api-Key"] == self.api_key
        request_json = mock_req.last_request.json()
        assert request_json["events"][0]["action_type"] == "add_two"
        assert request_json["events"][0]["params"] == {"x": 3, "y": 4}
        assert request_json["events"][0]["returns"] == 7

        agentops.end_session(end_state="Success")

    def test_record_action_decorator_multiple(self, mock_req):
        agentops.start_session()

        # Arrange
        @record_action(event_name=self.event_type)
        def add_three(x, y, z=3):
            return x + y + z

        # Act
        add_three(1, 2)
        add_three(1, 2, 4)

        time.sleep(1.5)

        # 3 requests: check_for_updates, start_session, record_action
        assert len(mock_req.request_history) == 3
        assert mock_req.last_request.headers["X-Agentops-Api-Key"] == self.api_key
        request_json = mock_req.last_request.json()

        assert request_json["events"][1]["action_type"] == self.event_type
        assert request_json["events"][1]["params"] == {"x": 1, "y": 2, "z": 4}
        assert request_json["events"][1]["returns"] == 7

        assert request_json["events"][0]["action_type"] == self.event_type
        assert request_json["events"][0]["params"] == {"x": 1, "y": 2, "z": 3}
        assert request_json["events"][0]["returns"] == 6

        agentops.end_session(end_state="Success")

    @pytest.mark.asyncio
    async def test_async_action_call(self, mock_req):
        agentops.start_session()

        @record_action(self.event_type)
        async def async_add(x, y):
            time.sleep(0.1)
            return x + y

        # Act
        result = await async_add(3, 4)
        time.sleep(0.1)

        # Assert
        assert result == 7
        # Assert
        assert len(mock_req.request_history) == 3
        assert mock_req.last_request.headers["X-Agentops-Api-Key"] == self.api_key
        request_json = mock_req.last_request.json()
        assert request_json["events"][0]["action_type"] == self.event_type
        assert request_json["events"][0]["params"] == {"x": 3, "y": 4}
        assert request_json["events"][0]["returns"] == 7

        init = datetime.fromisoformat(request_json["events"][0]["init_timestamp"])
        end = datetime.fromisoformat(request_json["events"][0]["end_timestamp"])

        assert (end - init).total_seconds() >= 0.1

        agentops.end_session(end_state="Success")

    def test_multiple_sessions_sync(self, mock_req):
        session_1 = agentops.start_session()
        session_2 = agentops.start_session()
        assert session_1 is not None
        assert session_2 is not None

        # Arrange
        @record_action(event_name=self.event_type)
        def add_three(x, y, z=3):
            return x + y + z

        # Act
        add_three(1, 2, session=session_1)
        time.sleep(0.1)
        add_three(1, 2, 3, session=session_2)
        time.sleep(0.1)

        assert len(mock_req.request_history) == 5

        request_json = mock_req.last_request.json()
        assert mock_req.last_request.headers["X-Agentops-Api-Key"] == self.api_key
        assert mock_req.last_request.headers["Authorization"] == "Bearer some_jwt2"
        assert request_json["events"][0]["action_type"] == self.event_type
        assert request_json["events"][0]["params"] == {"x": 1, "y": 2, "z": 3}
        assert request_json["events"][0]["returns"] == 6

        second_last_request_json = mock_req.request_history[-2].json()
        assert mock_req.request_history[-2].headers["X-Agentops-Api-Key"] == self.api_key
        assert mock_req.request_history[-2].headers["Authorization"] == "Bearer some_jwt"
        assert second_last_request_json["events"][0]["action_type"] == self.event_type
        assert second_last_request_json["events"][0]["params"] == {
            "x": 1,
            "y": 2,
            "z": 3,
        }
        assert second_last_request_json["events"][0]["returns"] == 6

        session_1.end_session(end_state="Success")
        session_2.end_session(end_state="Success")

    @pytest.mark.asyncio
    async def test_multiple_sessions_async(self, mock_req):
        session_1 = agentops.start_session()
        session_2 = agentops.start_session()
        assert session_1 is not None
        assert session_2 is not None

        # Arrange
        @record_action(self.event_type)
        async def async_add(x, y):
            time.sleep(0.1)
            return x + y

        # Act
        await async_add(1, 2, session=session_1)
        time.sleep(0.1)
        await async_add(1, 2, session=session_2)
        time.sleep(0.1)

        # Assert
        assert len(mock_req.request_history) == 5

        request_json = mock_req.last_request.json()
        assert mock_req.last_request.headers["X-Agentops-Api-Key"] == self.api_key
        assert mock_req.last_request.headers["Authorization"] == "Bearer some_jwt2"
        assert request_json["events"][0]["action_type"] == self.event_type
        assert request_json["events"][0]["params"] == {"x": 1, "y": 2}
        assert request_json["events"][0]["returns"] == 3

        second_last_request_json = mock_req.request_history[-2].json()
        assert mock_req.request_history[-2].headers["X-Agentops-Api-Key"] == self.api_key
        assert mock_req.request_history[-2].headers["Authorization"] == "Bearer some_jwt"
        assert second_last_request_json["events"][0]["action_type"] == self.event_type
        assert second_last_request_json["events"][0]["params"] == {
            "x": 1,
            "y": 2,
        }
        assert second_last_request_json["events"][0]["returns"] == 3

        session_1.end_session(end_state="Success")
        session_2.end_session(end_state="Success")

    def test_require_session_if_multiple(self):
        session_1 = agentops.start_session()
        session_2 = agentops.start_session()

        # Arrange
        @record_action(self.event_type)
        def add_two(x, y):
            time.sleep(0.1)
            return x + y

        with pytest.raises(ValueError):
            # Act
            add_two(1, 2)
