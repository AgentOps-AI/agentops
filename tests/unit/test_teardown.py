import pytest
import requests_mock

import agentops


class TestSessions:
    def test_exit(self, mock_req):
        url = "https://api.agentops.ai"
        api_key = "11111111-1111-4111-8111-111111111111"
        tool_name = "test_tool_name"
        agentops.init(api_key, max_wait_time=5, auto_start_session=False)
