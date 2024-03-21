import pytest
import requests_mock
import time
import agentops
from agentops import record_function
from datetime import datetime

@pytest.fixture
def mock_req():
    with requests_mock.Mocker() as m:
        url = 'https://api.agentops.ai'
        m.post(url + '/events', text='ok')
        m.post(url + '/sessions', text='ok')
        yield m

class TestRecordAction:
    def setup_method(self):
        self.url = 'https://api.agentops.ai'
        self.api_key = "random_api_key"
        self.event_type = 'test_event_type'
        agentops.init(self.api_key, max_wait_time=5, auto_start_session=False)
        agentops.start_session()

    def teardown_method(self):
        agentops.end_session(end_state='Success')

    def test_record_function_decorator(self, mock_req):
        @record_function(event_name=self.event_type)
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
        assert request_json['events'][0]['result'] == 'Success'
        assert request_json['events'][0]['tags'] == ['foo', 'bar']

    def test_record_function_decorator_multiple(self, mock_req):
        # Arrange
        @record_function(event_name=self.event_type)
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
        assert request_json['events'][0]['result'] == 'Success'
        assert request_json['events'][0]['tags'] == ['foo', 'bar']

    @pytest.mark.asyncio
    async def test_async_function_call(self, mock_req):

        @record_function(self.event_type)
        async def async_add(x, y):
            time.sleep(0.1)
            return x + y

        # Act
        result = await async_add(3, 4)
        time.sleep(0.1)

        # Assert
        assert result == 7
        # Assert
        assert len(mock_req.request_history) == 1
        assert mock_req.last_request.headers['X-Agentops-Auth'] == self.api_key
        request_json = mock_req.last_request.json()
        assert request_json['events'][0]['event_type'] == self.event_type
        assert request_json['events'][0]['params'] == {'x': 3, 'y': 4}
        assert request_json['events'][0]['returns'] == 7
        assert request_json['events'][0]['result'] == 'Success'
        init = datetime.fromisoformat(
            request_json['events'][0]['init_timestamp'].replace('Z', '+00:00'))
        end = datetime.fromisoformat(
            request_json['events'][0]['end_timestamp'].replace('Z', '+00:00'))

        assert (end - init).total_seconds() >= 0.1

    def test_function_call(self, mock_req):
        # Arrange
        prompt = 'prompt'

        @record_function(event_name=self.event_type)
        def foo(prompt=prompt):
            return 'output'

        # Act
        foo()
        time.sleep(0.1)

        # Assert
        assert len(mock_req.request_history) == 1
        request_json = mock_req.last_request.json()
        assert request_json['events'][0]['action_type'] == 'action'
        assert request_json['events'][0]['prompt'] == None
        assert request_json['events'][0]['returns'] == 'output'
        assert request_json['events'][0]['result'] == 'Success'

    def test_llm_call_no_action_type(self, mock_req):
        # Arrange
        prompt = 'prompt'

        @record_function(event_name=self.event_type)
        def llm_call(prompt=prompt):
            return 'output'

        llm_call()
        time.sleep(0.1)

        # Assert
        assert len(mock_req.request_history) == 1
        request_json = mock_req.last_request.json()
        assert request_json['events'][0]['action_type'] == 'action'
        assert request_json['events'][0]['prompt'] == None
        assert request_json['events'][0]['returns'] == 'output'
        assert request_json['events'][0]['result'] == 'Success'
