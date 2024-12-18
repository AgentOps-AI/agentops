import time
import requests_mock
import pytest
import agentops
from agentops import ActionEvent, ErrorEvent
from agentops.singleton import clear_singletons


@pytest.fixture(autouse=True)
def setup_teardown():
    clear_singletons()
    yield
    agentops.end_all_sessions()  # teardown part


@pytest.fixture(autouse=True, scope="function")
def mock_req():
    with requests_mock.Mocker() as m:
        url = "https://api.agentops.ai"
        api_key = "2a458d3f-5bd7-4798-b862-7d9a54515689"

        def match_headers(request):
            return (
                request.headers.get("X-Agentops-Api-Key") == api_key
                and (
                    request.headers.get("Authorization", "").startswith("Bearer ")
                    or request.path == "/v2/start_session"
                )
            )

        m.post(
            url + "/v2/start_session",
            json={"status": "success", "jwt": "test-jwt-token"},
            additional_matcher=match_headers,
        )
        m.post(url + "/v2/create_events", json={"status": "ok"}, additional_matcher=match_headers)
        m.post(url + "/v2/reauthorize_jwt", json={"status": "success", "jwt": "test-jwt-token"}, additional_matcher=match_headers)
        m.post(url + "/v2/update_session", json={"status": "success", "token_cost": 5}, additional_matcher=match_headers)
        m.post(url + "/v2/developer_errors", json={"status": "ok"}, additional_matcher=match_headers)
        m.post("https://pypi.org/pypi/agentops/json", status_code=404)
        yield m


class TestEvents:
    def setup_method(self):
        self.api_key = "11111111-1111-4111-8111-111111111111"
        self.event_type = "test_event_type"

    def test_record_timestamp(self, mock_req):
        agentops.init(api_key=self.api_key)

        event = ActionEvent()
        time.sleep(0.15)
        agentops.record(event)

        assert event.init_timestamp != event.end_timestamp

    def test_record_error_event(self, mock_req):
        agentops.init(api_key=self.api_key)

        event = ErrorEvent(logs=None)
        time.sleep(0.15)
        agentops.record(event)
