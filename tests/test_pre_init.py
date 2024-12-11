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
@pytest.fixture(autouse=True, scope="function")
def mock_req():
    with requests_mock.Mocker() as m:
        url = "https://api.agentops.ai"
        m.post(url + "/v2/create_agent", json={"status": "success"})
        m.post(url + "/v2/update_session", json={"status": "success", "token_cost": 5})
        m.post(url + "/v2/create_session", json={"status": "success", "jwt": "some_jwt"})
        m.post("https://pypi.org/pypi/agentops/json", status_code=404)

        m.post(url + "/v2/create_events", json={"status": "ok"})
        m.post(url + "/v2/developer_errors", json={"status": "ok"})

        yield m


@track_agent(name="TestAgent", skip_event=True)
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
        time.sleep(1)

        # Print request history for debugging
        print("\nInitial request history:")
        for i, req in enumerate(mock_req.request_history):
            print(f"\nRequest {i + 1}:")
            print(f"Method: {req.method}")
            print(f"URL: {req.url}")
            print(f"Headers: {dict(req.headers)}")
            try:
                print(f"Body: {req.json()}")
            except:
                print(f"Raw Body: {req.text}")
                print(f"Body Type: {type(req.text)}")

        # Assert
        # start session and create agent
        agentops.end_session(end_state="Success")

        # Wait for flush
        time.sleep(1.5)

        # Print final request history
        print("\nFinal request history:")
        for i, req in enumerate(mock_req.request_history):
            print(f"\nRequest {i + 1}:")
            print(f"Method: {req.method}")
            print(f"URL: {req.url}")
            print(f"Headers: {dict(req.headers)}")
            try:
                print(f"Body: {req.json()}")
            except:
                print(f"Raw Body: {req.text}")
                print(f"Body Type: {type(req.text)}")

        # 4 requests: check_for_updates, create_session, create_agent, update_session
        assert len(mock_req.request_history) == 4

        assert mock_req.request_history[-2].headers["X-Agentops-Api-Key"] == self.api_key

        mock_req.reset()
