import pytest
import requests_mock
import time
import agentops
from agentops import ActionEvent


@pytest.fixture
def mock_req():
    with requests_mock.Mocker() as m:
        url = 'https://api.agentops.ai'
        m.post(url + '/events', text='ok')
        m.post(url + '/sessions', text='ok')
        yield m


class TestCanary:
    def setup_method(self):
        self.url = 'https://api.agentops.ai'
        self.api_key = "random_api_key"
        agentops.init(api_key=self.api_key, max_wait_time=5, auto_start_session=False)

    def teardown_method(self):
        agentops.end_session(end_state='Success')

    def test_agent_ops_record(self, mock_req):
        # Arrange
        event_type = 'test_event_type'
        agentops.start_session()
        
        # Act
        agentops.record(ActionEvent(event_type))
        time.sleep(0.1)

        # Assert
        assert len(mock_req.request_history) == 2
        request_json = mock_req.last_request.json()
        assert mock_req.last_request.headers['X-Agentops-Auth'] == self.api_key
        assert request_json['events'][0]['event_type'] == event_type
