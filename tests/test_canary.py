import pytest
import requests_mock
import time
import agentops
from agentops import ActionEvent
from agentops.singleton import clear_singletons


@pytest.fixture(autouse=True)
def setup_teardown():
    clear_singletons()
    yield
    agentops.end_all_sessions()  # teardown part


@pytest.fixture(autouse=True, scope="function")
def mock_req():
    with requests_mock.Mocker() as m:
        base_url = "https://api.agentops.ai/v2"
        api_key = "2a458d3f-5bd7-4798-b862-7d9a54515689"

        def match_headers(request):
            headers = {k.lower(): v for k, v in request.headers.items()}
            return headers.get("x-agentops-api-key") == api_key and (
                headers.get("authorization", "").startswith("Bearer ") or request.path == "/v2/sessions/start"
            )

        # Mock v2 endpoints with consistent paths and response format
        m.post(
            f"{base_url}/sessions/start",
            json={"success": True, "jwt": "test-jwt-token", "session_url": "https://app.agentops.ai/session/123"},
            additional_matcher=match_headers,
        )
        m.post(f"{base_url}/sessions/test-session-id/events", json={"success": True}, additional_matcher=match_headers)
        m.post(
            f"{base_url}/sessions/test-session-id/jwt",
            json={"success": True, "jwt": "test-jwt-token"},
            additional_matcher=match_headers,
        )
        m.post(
            f"{base_url}/sessions/test-session-id/update",
            json={"success": True, "token_cost": 5},
            additional_matcher=match_headers,
        )
        m.post(f"{base_url}/sessions/test-session-id/end", json={"success": True}, additional_matcher=match_headers)
        yield m


class TestCanary:
    def setup_method(self):
        """Set up test environment"""
        clear_singletons()  # Reset singleton state
        agentops.end_all_sessions()  # Ensure clean state
        self.url = "https://api.agentops.ai"
        self.api_key = "2a458d3f-5bd7-4798-b862-7d9a54515689"
        agentops.init(api_key=self.api_key, max_wait_time=500, auto_start_session=False)

    def test_agent_ops_record(self, mock_req):
        # Arrange
        event_type = "test_event_type"
        agentops.start_session()

        # Act
        agentops.record(ActionEvent(event_type))
        time.sleep(2)

        # 3 requests: check_for_updates, create_session, create_events
        assert len(mock_req.request_history) == 3

        request_json = mock_req.last_request.json()
        assert mock_req.last_request.headers["X-Agentops-Api-Key"] == self.api_key
        assert request_json["events"][0]["event_type"] == event_type

        agentops.end_session("Success")
