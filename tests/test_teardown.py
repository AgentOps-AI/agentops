import pytest
import requests_mock
from agentops import Client


@pytest.fixture
def mock_req():
    with requests_mock.Mocker() as m:
        url = 'https://api.agentops.ai'
        m.post(url + '/v2/create_events', text='ok')
        m.post(url + '/v2/create_session', json={'status': 'success',
               'jwt': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'})
        m.post(url + '/v2/update_session',
               json={'status': 'success', 'token_cost': 5})
        m.post(url + '/v2/developer_errors', text='ok')
        yield m


class TestSessions:
    def setup_method(self):
        self.api_key = "random_api_key"
        self.event_type = 'test_event_type'
        self.client = Client(self.api_key)

    def test_exit(self):
        # Tests should not hang.
        ...
