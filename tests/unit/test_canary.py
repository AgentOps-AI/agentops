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

        # 3 requests: check_for_updates, create_session, create_events
        assert len(mock_req.request_history) == 3

        request_json = mock_req.last_request.json()
        assert mock_req.last_request.headers["X-Agentops-Api-Key"] == self.api_key
        assert request_json["events"][0]["event_type"] == event_type

        agentops.end_session("Success")
