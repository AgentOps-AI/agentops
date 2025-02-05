import contextlib
import time
from datetime import datetime

import pytest
import requests_mock

import agentops
from agentops import record_action, track_agent
from agentops.singleton import clear_singletons


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
        time.sleep(1)

        # Find agent creation request
        agent_requests = [r for r in mock_req.request_history if "/v2/create_agent" in r.url]
        assert len(agent_requests) > 0
        last_agent_request = agent_requests[-1]

        # Assert agent creation
        assert last_agent_request.headers["X-Agentops-Api-Key"] == self.api_key

        # End session and wait for flush
        agentops.end_session(end_state="Success")
        time.sleep(1.5)

        # Find session end request
        end_session_requests = [r for r in mock_req.request_history if "/v2/update_session" in r.url]
        assert len(end_session_requests) > 0
        last_end_request = end_session_requests[-1]

        assert last_end_request.headers["X-Agentops-Api-Key"] == self.api_key

        mock_req.reset()
