import time
import requests_mock
import pytest
import agentops
from agentops import ActionEvent, ErrorEvent


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


class TestEvents:
    def setup_method(self):
        self.api_key = "random_api_key"
        self.event_type = "test_event_type"
        self.config = agentops.Configuration(
            api_key=self.api_key, max_wait_time=50, max_queue_size=1
        )

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
