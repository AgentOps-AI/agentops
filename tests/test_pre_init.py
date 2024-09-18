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


@contextlib.contextmanager
@pytest.fixture(autouse=True)
def mock_req():
    with requests_mock.Mocker() as m:
        url = "https://api.agentops.ai"
        m.post(url + "/v2/create_agent", text="ok")
        m.post(url + "/v2/update_session", text="ok")
        m.post(
            url + "/v2/create_session", json={"status": "success", "jwt": "some_jwt"}
        )

        yield m


@track_agent(name="TestAgent")
class BasicAgent:
    def __init__(self):
        pass


class TestPreInit:
    def setup_method(self):
        self.url = "https://api.agentops.ai"
        self.api_key = "11111111-1111-4111-8111-111111111111"

    def test_track_agent(self, mock_req):
        agent = BasicAgent()

        assert len(mock_req.request_history) == 0

        agentops.init(api_key=self.api_key)

        # Assert
        # start session and create agent
        assert len(mock_req.request_history) == 2
        assert mock_req.last_request.headers["X-Agentops-Api-Key"] == self.api_key

        agentops.end_session(end_state="Success")
