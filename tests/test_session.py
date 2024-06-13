import pytest
import requests_mock
import time
import agentops
from agentops import ActionEvent


@pytest.fixture
def mock_req():
    with requests_mock.Mocker() as m:
        url = "https://api.agentops.ai"
        m.post(url + "/v2/create_events", text="ok")
        m.post(
            url + "/v2/create_session", json={"status": "success", "jwt": "some_jwt"}
        )
        m.post(
            url + "/v2/reauthorize_jwt", json={"status": "success", "jwt": "some_jwt"}
        )
        m.post(url + "/v2/update_session", json={"status": "success", "token_cost": 5})
        m.post(url + "/v2/developer_errors", text="ok")
        yield m


class TestSessions:
    def setup_method(self):
        self.api_key = "random_api_key"
        self.event_type = "test_event_type"
        self.config = agentops.Configuration(api_key=self.api_key, max_wait_time=50)

    def test_session(self, mock_req):
        agentops.start_session(config=self.config)

        agentops.record(ActionEvent(self.event_type))
        agentops.record(ActionEvent(self.event_type))

        # We should have 1 requests (session start).
        assert len(mock_req.request_history) == 1
        time.sleep(0.15)

        # We should have 2 requests (session and 2 events combined into 1)
        assert len(mock_req.request_history) == 2
        assert mock_req.last_request.headers["Authorization"] == f"Bearer some_jwt"
        request_json = mock_req.last_request.json()
        assert request_json["events"][0]["event_type"] == self.event_type

        end_state = "Success"
        agentops.end_session(end_state)
        time.sleep(0.15)

        # We should have 3 requests (additional end session)
        assert len(mock_req.request_history) == 3
        assert mock_req.last_request.headers["Authorization"] == f"Bearer some_jwt"
        request_json = mock_req.last_request.json()
        assert request_json["session"]["end_state"] == end_state
        assert request_json["session"]["tags"] == None

    def test_add_tags(self, mock_req):
        # Arrange
        tags = ["GPT-4"]
        agentops.start_session(tags=tags, config=self.config)
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

    def test_tags(self, mock_req):
        # Arrange
        tags = ["GPT-4"]
        agentops.start_session(tags=tags, config=self.config)

        # Act
        agentops.record(ActionEvent(self.event_type))
        time.sleep(0.15)

        # Assert 2 requests - 1 for session init, 1 for event
        print(mock_req.last_request.json())
        assert len(mock_req.request_history) == 2
        assert mock_req.last_request.headers["X-Agentops-Api-Key"] == self.api_key
        request_json = mock_req.last_request.json()
        assert request_json["events"][0]["event_type"] == self.event_type

        # Act
        end_state = "Success"
        agentops.end_session(end_state)
        time.sleep(0.15)

        # Assert 3 requests, 1 for session init, 1 for event, 1 for end session
        assert len(mock_req.request_history) == 3
        assert mock_req.last_request.headers["X-Agentops-Api-Key"] == self.api_key
        request_json = mock_req.last_request.json()
        assert request_json["session"]["end_state"] == end_state
        assert request_json["session"]["tags"] == tags

    def test_inherit_session_id(self, mock_req):
        # Arrange
        inherited_id = "4f72e834-ff26-4802-ba2d-62e7613446f1"
        agentops.start_session(
            tags=["test"], config=self.config, inherited_session_id=inherited_id
        )

        # Act
        # session_id correct
        request_json = mock_req.last_request.json()
        assert request_json["session_id"] == inherited_id

        # Act
        end_state = "Success"
        agentops.end_session(end_state)
        time.sleep(0.15)

        # Assert session ended with correct id
        request_json = mock_req.last_request.json()
        assert request_json["session"]["session_id"] == inherited_id
