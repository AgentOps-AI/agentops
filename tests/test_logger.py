import pytest
import requests_mock
import time
from agentops import Client, AgentOpsLogger


@pytest.fixture
def mock_req():
    with requests_mock.Mocker() as m:
        url = 'https://agentops-server-v2.fly.dev'
        m.post(url + '/events', text='ok')
        m.post(url + '/sessions', text='ok')
        yield m


class TestLogger:
    def setup_method(self):
        self.url = 'https://agentops-server-v2.fly.dev'
        self.api_key = "random_api_key"
        self.client = Client(api_key=self.api_key, max_wait_time=5)

    def teardown_method(self):
        self.client.end_session(end_state='Success')

    def test_info(self, mock_req):
        # Arrange
        self.event_type = "info"
        self.logger = AgentOpsLogger.get_agentops_logger(
            self.client, self.event_type)
        test_message = "Test info message"

        # Act
        try:
            self.logger.info(test_message)
        except Exception as e:
            pytest.fail(f"test_info failed with {e}")

        time.sleep(0.1)

        # Assert
        assert len(mock_req.request_history) == 1
        assert mock_req.last_request.headers['X-Agentops-Auth'] == self.api_key
        request_json = mock_req.last_request.json()
        assert request_json['events'][0]['event_type'] == f"{self.event_type}:INFO"
        assert request_json['events'][0]['returns'] == test_message

    def test_error(self, mock_req):
        # Arrange
        test_message = "Test error message"
        self.event_type = "error"
        self.logger = AgentOpsLogger.get_agentops_logger(
            self.client, self.event_type)

        # Act
        try:
            self.logger.error(test_message)
        except Exception as e:
            pytest.fail(f"test_error failed with {e}")

        time.sleep(0.1)

        # Assert
        assert len(mock_req.request_history) == 1
        assert mock_req.last_request.headers['X-Agentops-Auth'] == self.api_key
        request_json = mock_req.last_request.json()
        assert request_json['events'][0]['event_type'] == f"{self.event_type}:ERROR"
        assert request_json['events'][0]['returns'] == test_message

    def test_warn(self, mock_req):
        # Arrange
        test_message = "Test warn message"
        self.event_type = "warning"
        self.logger = AgentOpsLogger.get_agentops_logger(
            self.client, self.event_type)

        # Act
        try:
            self.logger.warning(test_message)
        except Exception as e:
            pytest.fail(f"test_warn failed with {e}")

        time.sleep(0.1)

        # Assert
        assert len(mock_req.request_history) == 1
        assert mock_req.last_request.headers['X-Agentops-Auth'] == self.api_key
        request_json = mock_req.last_request.json()
        assert request_json['events'][0]['event_type'] == f"{self.event_type}:WARNING"
        assert request_json['events'][0]['returns'] == test_message
