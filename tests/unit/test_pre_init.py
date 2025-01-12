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

        # Assert
        # start session and create agent
        agentops.end_session(end_state="Success")

        # Wait for flush
        time.sleep(1.5)

        # 4 requests: check_for_updates, create_session, create_agent, update_session
        assert len(mock_req.request_history) == 4

        assert mock_req.request_history[-2].headers["X-Agentops-Api-Key"] == self.api_key

        mock_req.reset()
