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


class TestSessions:
    def setup_method(self):
        self.api_key = "random_api_key"
        self.event_type = 'test_event_type'
        agentops.init(api_key=self.api_key, max_wait_time=5, auto_start_session=False)

    def test_session(self, mock_req):
        # Arrange
        agentops.start_session()

        # Act
        agentops.record(ActionEvent(self.event_type))

        # Assert the session has been initiated and the id has been created on backend.
        assert len(mock_req.request_history) == 1

        # Act
        agentops.record(ActionEvent(self.event_type))
        time.sleep(0.1)

        # Assert an event has been added
        assert len(mock_req.request_history) == 2
        assert mock_req.last_request.headers['X-Agentops-Auth'] == self.api_key
        request_json = mock_req.last_request.json()
        assert request_json['events'][0]['event_type'] == self.event_type

        # Act
        end_state = 'Success'
        agentops.end_session(end_state)
        time.sleep(0.1)

        # Since a session has ended, no more events should be recorded, but end_session should be called
        assert len(mock_req.request_history) == 3
        assert mock_req.last_request.headers['X-Agentops-Auth'] == self.api_key
        request_json = mock_req.last_request.json()
        assert request_json['session']['end_state'] == end_state
        assert request_json['session']['tags'] == None

    def test_tags(self, mock_req):
        # Arrange
        tags = ['GPT-4']
        agentops.start_session(tags=tags)

        # Act
        agentops.record(ActionEvent(self.event_type))
        time.sleep(0.1)

        # Assert 2 requests - 1 for session init, 1 for event
        assert len(mock_req.request_history) == 2
        assert mock_req.last_request.headers['X-Agentops-Auth'] == self.api_key
        request_json = mock_req.last_request.json()
        assert request_json['events'][0]['event_type'] == self.event_type

        # Act
        end_state = 'Success'
        agentops.end_session(end_state)
        time.sleep(0.1)

        # Assert 3 requets, 1 for session init, 1 for event, 1 for end session
        assert len(mock_req.request_history) == 3
        assert mock_req.last_request.headers['X-Agentops-Auth'] == self.api_key
        request_json = mock_req.last_request.json()
        assert request_json['session']['end_state'] == end_state
        assert request_json['session']['tags'] == tags