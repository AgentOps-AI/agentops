import pytest
import requests_mock
import time

from agentops import Client, Event, EventState


@pytest.fixture
def mock_req():
    with requests_mock.Mocker() as m:
        url = 'https://agentops-server-v2.fly.dev'
        m.post(url + '/events', text='ok')
        m.post(url + '/sessions', text='ok')
        yield m


class TestSessions:
    def setup_method(self):
        self.api_key = "random_api_key"
        self.event_type = 'test_event_type'

    def test_session(self, mock_req):
        # Arrange
        client = Client(api_key=self.api_key, max_wait_time=5)

        # Act
        client.record(Event(self.event_type))

        # Assert the session has been initiated and the id has been created on backend.
        assert len(mock_req.request_history) == 1

        # Act
        client.record(Event(self.event_type))
        time.sleep(0.1)

        # Assert an event has been added
        assert len(mock_req.request_history) == 2
        assert mock_req.last_request.headers['X-Agentops-Auth'] == self.api_key
        request_json = mock_req.last_request.json()
        assert request_json['events'][0]['event_type'] == self.event_type

        # Act
        end_state = EventState.SUCCESS
        client.end_session(end_state)
        time.sleep(0.1)

        # Since a session has ended, no more events should be recorded, but end_session should be called
        assert len(mock_req.request_history) == 3
        assert mock_req.last_request.headers['X-Agentops-Auth'] == self.api_key
        request_json = mock_req.last_request.json()
        assert request_json['session']['rating'] == None
        assert request_json['session']['end_state'] == end_state
        assert request_json['session']['tags'] == None

    def test_tags(self, mock_req):
        # Arrange
        tags = ['GPT-4']
        client = Client(api_key=self.api_key, tags=tags, max_wait_time=5)

        # Act
        client.record(Event(self.event_type))
        time.sleep(0.1)

        # Assert 2 requests - 1 for session init, 1 for event
        assert len(mock_req.request_history) == 2
        assert mock_req.last_request.headers['X-Agentops-Auth'] == self.api_key
        request_json = mock_req.last_request.json()
        assert request_json['events'][0]['event_type'] == self.event_type

        # Act
        end_state = EventState.SUCCESS
        client.end_session(end_state)
        time.sleep(0.1)

        # Assert 3 requets, 1 for session init, 1 for event, 1 for end session
        assert len(mock_req.request_history) == 3
        assert mock_req.last_request.headers['X-Agentops-Auth'] == self.api_key
        request_json = mock_req.last_request.json()
        assert request_json['session']['rating'] == None
        assert request_json['session']['end_state'] == end_state
        assert request_json['session']['tags'] == tags


class TestRecordAction:
    def setup_method(self):
        self.url = 'https://agentops-server-v2.fly.dev'
        self.api_key = "random_api_key"
        self.event_type = 'test_event_type'
        self.client = Client(self.api_key, max_wait_time=5)

    def teardown_method(self):
        self.client.end_session(end_state=EventState.SUCCESS)

    def test_record_action_decorator(self, mock_req):
        @self.client.record_action(event_name=self.event_type, tags=['foo', 'bar'])
        def add_two(x, y):
            return x + y

        # Act
        add_two(3, 4)
        time.sleep(0.1)

        # Assert
        assert len(mock_req.request_history) == 1
        assert mock_req.last_request.headers['X-Agentops-Auth'] == self.api_key
        request_json = mock_req.last_request.json()
        assert request_json['events'][0]['event_type'] == self.event_type
        assert request_json['events'][0]['params'] == {'x': 3, 'y': 4}
        assert request_json['events'][0]['returns'] == 7
        assert request_json['events'][0]['result'] == EventState.SUCCESS
        assert request_json['events'][0]['tags'] == ['foo', 'bar']

    def test_record_action_decorator_multiple(self, mock_req):
        # Arrange
        @self.client.record_action(event_name=self.event_type, tags=['foo', 'bar'])
        def add_three(x, y, z=3):
            return x + y + z

        # Act
        add_three(1, 2)
        time.sleep(0.1)

        # Assert
        assert len(mock_req.request_history) == 1
        assert mock_req.last_request.headers['X-Agentops-Auth'] == self.api_key
        request_json = mock_req.last_request.json()
        assert request_json['events'][0]['event_type'] == self.event_type
        assert request_json['events'][0]['params'] == {'x': 1, 'y': 2, 'z': 3}
        assert request_json['events'][0]['returns'] == 6
        assert request_json['events'][0]['result'] == EventState.SUCCESS
        assert request_json['events'][0]['tags'] == ['foo', 'bar']

    def test_llm_call(self, mock_req):
        # Arrange
        prompt = 'prompt'

        @self.client.record_action(event_name=self.event_type, action_type='llm', model='gpt-4')
        def llm_call(prompt=prompt):
            return 'output'

        # Act
        llm_call()
        time.sleep(0.1)

        # Assert
        assert len(mock_req.request_history) == 1
        request_json = mock_req.last_request.json()
        assert request_json['events'][0]['action_type'] == 'llm'
        assert request_json['events'][0]['prompt'] == prompt
        assert request_json['events'][0]['returns'] == 'output'
        assert request_json['events'][0]['result'] == EventState.SUCCESS

    def test_llm_call_no_prompt(self, mock_req):
        # Arrange
        @self.client.record_action(event_name=self.event_type,
                                   action_type='llm', model='gpt-4')
        def llm_call():
            return 'output'

        # Act and Assert
        with pytest.raises(ValueError):
            llm_call()

    def test_llm_call_no_model(self, mock_req):
        # Arrange
        prompt = 'prompt'

        @self.client.record_action(event_name=self.event_type, action_type='llm')
        def llm_call(prompt=prompt):
            return 'output'

        # Act and Assert
        with pytest.raises(ValueError):
            llm_call()

    def test_llm_call_no_action_type(self, mock_req):
        # Arrange
        prompt = 'prompt'

        @self.client.record_action(event_name=self.event_type, model='gpt-4')
        def llm_call(prompt=prompt):
            return 'output'

        llm_call()
        time.sleep(0.1)

        # Assert
        assert len(mock_req.request_history) == 1
        request_json = mock_req.last_request.json()
        assert request_json['events'][0]['action_type'] == 'llm'
        assert request_json['events'][0]['prompt'] == prompt
        assert request_json['events'][0]['returns'] == 'output'
        assert request_json['events'][0]['result'] == EventState.SUCCESS
