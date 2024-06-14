import pytest
import requests_mock
from agentops import Client


@pytest.fixture
def mock_req():
    with requests_mock.Mocker() as m:
        url = "https://api.agentops.ai"
        m.post(url + "/v2/create_events", text="ok")
        m.post(
            url + "/v2/create_session", json={"status": "success", "jwt": "some_jwt"}
        )
        m.post(url + "/v2/update_session", json={"status": "success", "token_cost": 5})
        m.post(url + "/v2/developer_errors", text="ok")
        yield m


class TestSessions:
    def setup_method(self):
        self.api_key = "random_api_key"
        self.event_type = "test_event_type"
        self.client = Client(self.api_key, allow_multiple_instances=False)

    def test_exit(self):
        # Tests should not hang.
        ...

    def test_can_stop_with_no_instrumentation(self):
        non_instrumented = Client(self.api_key, instrument_llm_calls=False,
                                  allow_multiple_instances=True)
        non_instrumented.stop_instrumenting()
