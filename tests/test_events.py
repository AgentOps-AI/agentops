import time
import pytest
import requests_mock

import agentops
from agentops import Event, ActionEvent, ErrorEvent
from agentops.http_client import HttpClient
from agentops.singleton import clear_singletons


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
        base_url = "http://localhost/v2"  # Use localhost for test mode
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
        m.post(
            f"{base_url}/sessions/test-session-id/events",
            json={"success": True},
            additional_matcher=match_headers,
        )
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
        m.post(
            f"{base_url}/sessions/test-session-id/end",
            json={"success": True},
            additional_matcher=match_headers,
        )
        yield m


class TestEvents:
    def setup_method(self):
        """Set up test environment"""
        clear_singletons()  # Reset singleton state
        agentops.end_all_sessions()  # Ensure clean state
        self.api_key = "2a458d3f-5bd7-4798-b862-7d9a54515689"
        self.event_type = "test_event_type"

    def test_record_timestamp(self, mock_req):
        agentops.init(api_key=self.api_key)

        event = ActionEvent()
        time.sleep(0.15)
        try:
            agentops.record(event)
            assert event.init_timestamp != event.end_timestamp
        except Exception as e:
            pytest.fail(f"Record failed: {str(e)}")

    def test_record_error_event(self, mock_req):
        agentops.init(api_key=self.api_key)

        event = ErrorEvent(logs=None)
        time.sleep(0.15)
        try:
            agentops.record(event)
        except Exception as e:
            pytest.fail(f"Record failed: {str(e)}")
