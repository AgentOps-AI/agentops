import pytest
import requests_mock
import time
import agentops
from agentops import ActionEvent
from agentops.enums import EventType
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
        m.post(url + "/v2/create_events", json={"status": "success"})
        m.post(url + "/v2/create_session", json={"status": "success", "jwt": "some_jwt"})
        m.post(url + "/v2/update_session", json={"status": "success", "token_cost": 5})
        m.post(url + "/v2/developer_errors", json={"status": "success"})
        m.post("https://pypi.org/pypi/agentops/json", status_code=404)
        yield m


class TestCanary:
    def setup_method(self):
        self.url = "https://api.agentops.ai"
        self.api_key = "11111111-1111-4111-8111-111111111111"
        agentops.init(api_key=self.api_key, max_wait_time=500, auto_start_session=False)

    def test_agent_ops_record(self, mock_req):
        # Arrange
        event_type = EventType.ACTION
        agentops.start_session()

        # Act
        agentops.record(ActionEvent(event_type=event_type))
        time.sleep(2)

        # 3 requests: check_for_updates, create_session, create_events
        assert len(mock_req.request_history) == 3

        request_json = mock_req.last_request.json()
        assert mock_req.last_request.headers["X-AgentOps-Api-Key"] == self.api_key
        assert request_json["events"][0]["event_type"] == EventType.ACTION.value

        agentops.end_session("Success")
