import time

import pytest
import requests_mock

import agentops
from agentops import ActionEvent


class TestCanary:
    def setup_method(self):
        self.url = "https://api.agentops.ai"
        self.api_key = "11111111-1111-4111-8111-111111111111"
        agentops.init(api_key=self.api_key, max_wait_time=500, auto_start_session=False)

    def test_agent_ops_record(self, mock_req):
        # Arrange
        event_type = "test_event_type"
        agentops.start_session()

        # Act
        agentops.record(ActionEvent(event_type))
        time.sleep(2)

        # Find event requests
        event_requests = [r for r in mock_req.request_history if "/v2/create_events" in r.url]
        assert len(event_requests) > 0
        last_event_request = event_requests[-1]

        assert last_event_request.headers["X-Agentops-Api-Key"] == self.api_key
        request_json = last_event_request.json()
        assert request_json["events"][0]["event_type"] == event_type

        agentops.end_session("Success")
