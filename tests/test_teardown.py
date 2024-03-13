import pytest
import requests_mock
import sys

from agentops import Client


@pytest.fixture
def mock_req():
    with requests_mock.Mocker() as m:
        url = 'https://api.agentops.ai'
        m.post(url + '/events', text='ok')
        m.post(url + '/sessions', text='ok')
        yield m


class TestSessions:
    def setup_method(self):
        self.api_key = "random_api_key"
        self.event_type = 'test_event_type'
        self.client = Client(self.api_key)

    def test_exit(self):
        # Tests should not hang.
        ...
