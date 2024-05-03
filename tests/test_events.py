import time
import requests_mock
import pytest
import agentops
from agentops import ActionEvent


@pytest.fixture
def mock_req():
    with requests_mock.Mocker() as m:
        url = 'https://api.agentops.ai'
        m.post(url + '/events', text='ok')
        m.post(url + '/sessions', json={'status': 'success', 'token_cost': 5})
        yield m

class TestEvents:
    def setup_method(self):
        self.api_key = "random_api_key"
        self.event_type = 'test_event_type'
        self.config = agentops.Configuration(api_key=self.api_key, max_wait_time=50, max_queue_size=1)

    def test_record_timestamp(self, mock_req):
        # agentops.init(api_key=self.api_key, max_wait_time=50, auto_start_session=False)
        agentops.init(api_key=self.api_key)
        agentops.start_session(config=self.config)

        event = ActionEvent(self.event_type)
        time.sleep(0.15)
        agentops.record(event)

        assert event.init_timestamp != event.end_timestamp