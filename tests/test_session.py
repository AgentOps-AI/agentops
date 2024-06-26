import pytest
import requests_mock
import time
import agentops
from agentops import ActionEvent, Client
from agentops.helpers import clear_singletons


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
        m.post(
            url + "/v2/reauthorize_jwt", json={"status": "success", "jwt": "some_jwt"}
        )
        m.post(url + "/v2/update_session", json={"status": "success", "token_cost": 5})
        m.post(url + "/v2/developer_errors", text="ok")
        yield m


class TestSingleSessions:
    def setup_method(self):
        self.api_key = "random_api_key"
        self.event_type = "test_event_type"
        self.config = agentops.ClientConfiguration(
            api_key=self.api_key, max_wait_time=50
        )

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

        agentops.end_all_sessions()

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

        agentops.end_all_sessions()

    def test_tags(self, mock_req):
        # Arrange
        tags = ["GPT-4"]
        agentops.start_session(tags=tags, config=self.config)

        # Act
        agentops.record(ActionEvent(self.event_type))

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

        agentops.end_all_sessions()

    def test_inherit_session_id(self, mock_req):
        # Arrange
        inherited_id = "4f72e834-ff26-4802-ba2d-62e7613446f1"
        agentops.start_session(
            tags=["test"], config=self.config, inherited_session_id=inherited_id
        )

        # Act
        # session_id correct
        request_json = mock_req.last_request.json()
        assert request_json["session"]["session_id"] == inherited_id

        # Act
        end_state = "Success"
        agentops.end_session(end_state)
        time.sleep(0.15)

        agentops.end_all_sessions()

    def test_add_tags_with_string(self, mock_req):
        agentops.start_session(config=self.config)
        agentops.add_tags("wrong-type-tags")

        request_json = mock_req.last_request.json()
        assert request_json["session"]["tags"] == ["wrong-type-tags"]

    def test_session_add_tags_with_string(self, mock_req):
        session = agentops.start_session(config=self.config)
        session.add_tags("wrong-type-tags")

        request_json = mock_req.last_request.json()
        assert request_json["session"]["tags"] == ["wrong-type-tags"]

    def test_set_tags_with_string(self, mock_req):
        agentops.start_session(config=self.config)
        agentops.set_tags("wrong-type-tags")

        request_json = mock_req.last_request.json()
        assert request_json["session"]["tags"] == ["wrong-type-tags"]

    def test_session_set_tags_with_string(self, mock_req):
        session = agentops.start_session(config=self.config)
        session.set_tags("wrong-type-tags")

        request_json = mock_req.last_request.json()
        assert request_json["session"]["tags"] == ["wrong-type-tags"]

    def test_add_tags_before_session(self, mock_req):
        agentops.add_tags(["pre-session-tag"])
        agentops.start_session(config=self.config)

        request_json = mock_req.last_request.json()
        assert request_json["session"]["tags"] == ["pre-session-tag"]

    def test_set_tags_before_session(self, mock_req):
        agentops.set_tags(["pre-session-tag"])
        agentops.start_session(config=self.config)

        request_json = mock_req.last_request.json()
        assert request_json["session"]["tags"] == ["pre-session-tag"]

    def test_no_config_doesnt_start_session(self, mock_req):
        session = agentops.start_session()
        assert session is None

    def test_safe_get_session_no_session(self, mock_req):
        with pytest.raises(ValueError):
            session = Client()._safe_get_session()

    def test_safe_get_session_with_session(self, mock_req):
        agentops.start_session(config=self.config)
        session = Client()._safe_get_session()
        assert session is not None

    def test_safe_get_session_with_multiple_sessions(self, mock_req):
        agentops.start_session(config=self.config)
        agentops.start_session(config=self.config)

        with pytest.raises(ValueError):
            session = Client()._safe_get_session()


class TestMultiSessions:
    def setup_method(self):
        self.api_key = "random_api_key"
        self.event_type = "test_event_type"
        self.config = agentops.ClientConfiguration(
            api_key=self.api_key, max_wait_time=50
        )

    def test_two_sessions(self, mock_req):
        session_1 = agentops.start_session(config=self.config)
        session_2 = agentops.start_session(config=self.config)

        assert len(agentops.Client().current_session_ids) == 2
        assert agentops.Client().current_session_ids == [
            str(session_1.session_id),
            str(session_2.session_id),
        ]

        # We should have 2 requests (session starts).
        assert len(mock_req.request_history) == 2

        session_1.record(ActionEvent(self.event_type))
        session_2.record(ActionEvent(self.event_type))

        time.sleep(1.5)

        # We should have 4 requests (2 sessions and 2 events each in their own request)
        assert len(mock_req.request_history) == 4
        assert mock_req.last_request.headers["Authorization"] == f"Bearer some_jwt"
        request_json = mock_req.last_request.json()
        assert request_json["events"][0]["event_type"] == self.event_type

        end_state = "Success"

        session_1.end_session(end_state)
        time.sleep(1.5)

        # We should have 6 requests (2 additional end sessions)
        assert len(mock_req.request_history) == 5
        assert mock_req.last_request.headers["Authorization"] == f"Bearer some_jwt"
        request_json = mock_req.last_request.json()
        assert request_json["session"]["end_state"] == end_state
        assert request_json["session"]["tags"] is None

        session_2.end_session(end_state)
        # We should have 6 requests (2 additional end sessions)
        assert len(mock_req.request_history) == 6
        assert mock_req.last_request.headers["Authorization"] == f"Bearer some_jwt"
        request_json = mock_req.last_request.json()
        assert request_json["session"]["end_state"] == end_state
        assert request_json["session"]["tags"] is None

    def test_add_tags(self, mock_req):
        # Arrange
        session_1_tags = ["session-1"]
        session_2_tags = ["session-2"]

        session_1 = agentops.start_session(tags=session_1_tags, config=self.config)
        session_2 = agentops.start_session(tags=session_2_tags, config=self.config)

        session_1.add_tags(["session-1-added", "session-1-added-2"])
        session_2.add_tags(["session-2-added"])

        # Act
        end_state = "Success"
        session_1.end_session(end_state)
        session_2.end_session(end_state)
        time.sleep(0.15)

        # Assert 3 requests, 1 for session init, 1 for event, 1 for end session
        req1 = mock_req.request_history[-1].json()
        req2 = mock_req.request_history[-2].json()

        session_1_req = (
            req1 if req1["session"]["session_id"] == session_1.session_id else req2
        )
        session_2_req = (
            req2 if req2["session"]["session_id"] == session_2.session_id else req1
        )

        assert session_1_req["session"]["end_state"] == end_state
        assert session_2_req["session"]["end_state"] == end_state

        assert session_1_req["session"]["tags"] == [
            "session-1",
            "session-1-added",
            "session-1-added-2",
        ]

        assert session_2_req["session"]["tags"] == [
            "session-2",
            "session-2-added",
        ]
