import pytest
import requests_mock
import time
import agentops
from agentops import record_action, track_agent
from datetime import datetime
from agentops.singleton import clear_singletons
import contextlib

jwts = ["some_jwt", "some_jwt2", "some_jwt3"]


@pytest.fixture(autouse=True)
def setup_teardown():
    clear_singletons()
    yield
    agentops.end_all_sessions()  # teardown part


@pytest.fixture(autouse=True, scope="function")
def mock_req():
    """Set up mock requests."""
    with requests_mock.Mocker() as m:
        base_url = "/v2"
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
        m.post(f"{base_url}/sessions/test-session-id/agent", json={"success": True}, additional_matcher=match_headers)
        m.post("https://pypi.org/pypi/agentops/json", status_code=404)

        yield m


@track_agent(name="TestAgent")
class BasicAgent:
    def __init__(self):
        pass


class TestPreInit:
    def setup_method(self):
        """Set up test environment"""
        clear_singletons()  # Reset singleton state
        agentops.end_all_sessions()  # Ensure clean state
        self.url = "https://api.agentops.ai"
        self.api_key = "2a458d3f-5bd7-4798-b862-7d9a54515689"

    def test_track_agent(self, mock_req):
        agent = BasicAgent()

        assert len(mock_req.request_history) == 0

        agentops.init(api_key=self.api_key)
        time.sleep(1)

        # Assert
        # start session and create agent
        try:
            agentops.end_session(end_state="Success")

            # Wait for flush
            time.sleep(1.5)

            # 4 requests: check_for_updates, create_session, create_agent, update_session
            assert len(mock_req.request_history) == 4
            assert mock_req.request_history[-2].headers["x-agentops-api-key"] == self.api_key
        except Exception as e:
            pytest.fail(f"Test failed: {str(e)}")

        mock_req.reset()
