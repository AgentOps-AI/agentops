from unittest import mock

import pytest
from opentelemetry.sdk.trace import SpanProcessor
from opentelemetry.sdk.trace.export import SpanExporter
from pytest_mock import MockerFixture

import agentops
from agentops.client import Client
from agentops.exceptions import (AgentOpsClientNotInitializedException,
                                 NoApiKeyException, NoSessionException)
from agentops.session import Session


@pytest.fixture(autouse=True)
def mock_session(mocker: MockerFixture):
    mock_session = mocker.patch("agentops.client.Session", autospec=True)
    yield mock_session


@pytest.fixture(autouse=True)
def no_prefetch_jwt_token(agentops_config):
    agentops_config.prefetch_jwt_token = False


@pytest.fixture(autouse=True)
def no_auto_init(agentops_config):
    agentops_config.auto_init = False



class TestClient:
    def test_client_init_configuration(self, api_key):
        """Test client initialization with configuration parameters"""
        # Set up test values
        test_endpoint = "https://test-api.agentops.ai"
        test_tags = ["test", "unit"]

        # Initialize client with test values
        client = Client()
        client.init(
            api_key=api_key,
            endpoint=test_endpoint,
            default_tags=test_tags,
            auto_start_session=False,
            instrument_llm_calls=False,
        )

        # Verify config values were set correctly
        assert client.config.api_key == api_key
        assert client.config.endpoint == test_endpoint
        assert set(test_tags).issubset(client.config.default_tags)
        assert client.config.auto_start_session is False
        assert client.config.instrument_llm_calls is False
        assert client.initialized is True

    def test_auto_start_session(self, mock_session: mock.MagicMock, api_key):
        """Test that auto_start_session creates a session during init"""
        # Set up client with auto_start_session=True
        client = Client()
        session = client.init(api_key=api_key, auto_start_session=True)

        # Verify a session was created
        assert mock_session.called, "Session should be created with client.init(auto_start_session=True)"
        assert session is mock_session.return_value, (
            "client.init(auto_start_session=True) should return the created session"
        )

    @mock.patch("agentops.client.Client.init")
    def test_start_session_uninitialized_with_auto_init(self, client_init_mock, no_auto_init):
        """Test starting a session when client is not initialized but auto_init is True"""
        # Create client but don't initialize it
        client = Client()

        # Start a session
        client.start_session()

        # Verify init was called
        client_init_mock.assert_called_once()

    def test_start_session_uninitialized_without_auto_init(self):
        """Test starting a session when client is not initialized and auto_init is False"""
        # Create client but don't initialize it
        client = Client()
        client.config.auto_init = False

        # Starting a session should raise an exception
        with pytest.raises(AgentOpsClientNotInitializedException):
            client.start_session()

    def test_start_session_without_api_key(self):
        """Test starting a session without an API key"""
        # Initialize client without API key
        client = Client()
        client.initialized = True
        client.config.api_key = None

        # Starting a session should raise an exception
        with pytest.raises(NoApiKeyException):
            client.start_session()

    def test_session_creation_exception_without_fail_safe(self, mock_session, api_key):
        """Test that exceptions during session creation are raised when fail_safe is False"""
        # Mock Session to raise an exception
        mock_session.side_effect = Exception("Test exception")

        # Initialize client with fail_safe=False, but don't auto-start session
        client = Client()
        client.init(api_key=api_key, fail_safe=False, auto_start_session=False)

        # Start a session - should raise the exception
        with pytest.raises(Exception, match="Test exception"):
            client.start_session()

    @mock.patch("agentops.client.get_default_session")
    def test_end_session(self, mock_get_default_session):
        """Test ending a session"""
        # Set up mock session
        mock_session = mock.MagicMock()
        mock_get_default_session.return_value = mock_session

        # End the session
        client = Client()
        client.end_session("Success", "Test completed")

        # Verify session.end was called with correct parameters
        mock_session.end.assert_called_once_with("Success", "Test completed", None)

    @mock.patch("agentops.client.get_default_session")
    def test_end_session_no_active_session(self, mock_get_default_session):
        """Test ending a session when no session is active"""
        # No active session
        mock_get_default_session.return_value = None

        # End the session - should not raise
        client = Client()
        client.end_session("Success", "Test completed")

    @mock.patch("agentops.client.get_active_sessions")
    def test_end_all_sessions(self, mock_get_active_sessions):
        """Test ending all active sessions"""
        # Set up mock sessions
        mock_session1 = mock.MagicMock()
        mock_session2 = mock.MagicMock()
        mock_get_active_sessions.return_value = [mock_session1, mock_session2]

        # End all sessions
        client = Client()
        client.end_all_sessions()

        # Verify end was called on each session
        mock_session1.end.assert_called_once()
        mock_session2.end.assert_called_once()


    def test_initialized_property(self):
        """Test the initialized property and setter"""
        client = Client()
        assert client.initialized is False

        client.initialized = True
        assert client.initialized is True

        # Setting to the same value should work
        client.initialized = True

        # Setting to a different value after initialized=True should raise
        with pytest.raises(ValueError, match="Client already initialized"):
            client.initialized = False

    # Tests from test_client_session_integration.py
    def test_client_init_auto_start_session(self, api_key, mock_req):
        """Test that auto_start_session=True creates a session during init"""
        # Initialize client with auto_start_session=True
        client = Client()
        returned_session = client.init(api_key=api_key, auto_start_session=True)

        # Verify a session was created and returned
        assert returned_session is not None
        assert isinstance(returned_session, Session)

        # Verify API call was made to create the session
        assert any(call.url.endswith("/v2/create_session") for call in mock_req.request_history)

    def test_client_init_no_auto_start_session(self, api_key, mock_req):
        """Test that auto_start_session=False doesn't create a session during init"""
        # Initialize client with auto_start_session=False
        client = Client()
        returned_session = client.init(api_key=api_key, auto_start_session=False)

        # Verify no session was returned
        assert returned_session is None

        # Verify no API call was made to create a session
        assert not any(call.url.endswith("/v2/create_session") for call in mock_req.request_history)

    @mock.patch("agentops.client.get_default_session")
    def test_client_session_tags(self, mock_get_default_session, api_key, mock_req):
        """Test adding and setting tags on a session through the client"""
        # Create a mock session
        mock_session = mock.MagicMock()
        mock_get_default_session.return_value = mock_session

        # Initialize client
        client = Client()
        client.init(api_key=api_key, auto_start_session=False)

        # Add tags through the client
        client.add_tags(["tag1", "tag2"])

        # Verify add_tags was called on the session
        mock_session.add_tags.assert_called_once_with(["tag1", "tag2"])

        # Set new tags through the client
        client.set_tags(["tag3", "tag4"])

        # Verify set_tags was called on the session
        mock_session.set_tags.assert_called_once_with(["tag3", "tag4"])

    def test_client_session_tags_no_session(self):
        """Test that adding tags with no session raises an exception"""
        # Initialize client without starting a session
        client = Client()
        client.init(api_key="test-key", auto_start_session=False)

        # Add tags through the client should raise NoSessionException
        with pytest.raises(NoSessionException):
            client.add_tags(["tag1", "tag2"])

        # Set tags through the client should raise NoSessionException
        with pytest.raises(NoSessionException):
            client.set_tags(["tag3", "tag4"])

    @mock.patch("agentops.client.get_default_session")
    def test_client_end_session(self, mock_get_default_session, api_key, mock_req):
        """Test ending a session through the client"""
        # Create a mock session
        mock_session = mock.MagicMock()
        mock_get_default_session.return_value = mock_session

        # Initialize client
        client = Client()
        client.init(api_key=api_key, auto_start_session=False)

        # End the session through the client
        client.end_session("SUCCEEDED", "Test completed")

        # Verify end was called on the session with correct parameters
        mock_session.end.assert_called_once_with("SUCCEEDED", "Test completed", None)

    @mock.patch("agentops.client.get_active_sessions")
    def test_end_all_sessions_integration(self, mock_get_active_sessions, api_key, mock_req):
        """Test end_all_sessions with actual Session interactions"""
        # Create mock sessions
        mock_session1 = mock.MagicMock()
        mock_session2 = mock.MagicMock()
        mock_get_active_sessions.return_value = [mock_session1, mock_session2]

        # Initialize client
        client = Client()
        client.init(api_key=api_key, auto_start_session=False)

        # End all sessions
        client.end_all_sessions()

        # Verify end was called on each session with the expected parameters
        mock_session1.end.assert_called_once_with("Indeterminate", "Forced end via end_all_sessions()")
        mock_session2.end.assert_called_once_with("Indeterminate", "Forced end via end_all_sessions()")
