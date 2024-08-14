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


class TestCanary:
    def setup_method(self):
        self.url = "https://api.agentops.ai"
        self.api_key = "11111111-1111-4111-8111-111111111111"
        agentops.init(api_key=self.api_key, max_wait_time=5, auto_start_session=False)

    def test_agent_ops_record(self, mock_req):
        # Arrange
        event_type = "test_event_type"
        agentops.start_session()

        # Act
        agentops.record(ActionEvent(event_type))
        time.sleep(0.1)

        # Assert
        assert len(mock_req.request_history) == 2
        request_json = mock_req.last_request.json()
        assert mock_req.last_request.headers["X-Agentops-Api-Key"] == self.api_key
        assert request_json["events"][0]["event_type"] == event_type

        agentops.end_session("Success")
