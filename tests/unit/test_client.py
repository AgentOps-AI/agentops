import uuid
import pytest
from unittest import mock

import agentops
from agentops.client import Client
from agentops._singleton import ao_instances, clear_singletons
from agentops.exceptions import AgentOpsClientNotInitializedException, NoApiKeyException
from agentops.instrumentation import instrument_all, uninstrument_all
from agentops.session import Session


@pytest.fixture(autouse=True)
def reset_client():
    """Reset the client singleton before and after each test"""
    clear_singletons()
    # Ensure any instrumentation is cleared
    with mock.patch('agentops.instrumentation.instrument_all'):
        with mock.patch('agentops.instrumentation.uninstrument_all'):
            yield
    clear_singletons()


class TestClient:
    def test_client_is_singleton(self):
        """Test that Client is a singleton by default"""
        # Create two instances
        client1 = Client()
        client2 = Client()
        
        # They should be the same object
        assert client1 is client2
        
        # Clear the singletons to create a fresh instance
        clear_singletons()
        
        # Create a new instance after clearing
        client3 = Client()
        
        # Should be different from previous instances
        assert client3 is not client1
        
        # But new instances should still be singletons
        client4 = Client()
        assert client3 is client4
    
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
            instrument_llm_calls=False
        )
        
        # Verify config values were set correctly
        assert client.config.api_key == api_key
        assert client.config.endpoint == test_endpoint
        assert set(test_tags).issubset(client.config.default_tags)
        assert client.config.auto_start_session is False
        assert client.config.instrument_llm_calls is False
        assert client.initialized is True
    
    @mock.patch('agentops.client.instrument_all')
    def test_auto_instrumentation(self, mock_instrument_all, api_key):
        """Test that instrumentation is enabled when the flag is set"""
        client = Client()
        client.init(api_key=api_key, auto_start_session=False, instrument_llm_calls=True)
        
        # Verify instrumentation was called
        mock_instrument_all.assert_called_once()
    
    @mock.patch('agentops.client.Session')
    def test_auto_start_session(self, mock_session, api_key):
        """Test that auto_start_session creates a session during init"""
        # Set up client with auto_start_session=True
        client = Client()
        session = client.init(api_key=api_key, auto_start_session=True)
        
        # Verify a session was created
        mock_session.assert_called_once()
        assert session is mock_session.return_value
    
    def test_start_session_uninitialized_with_auto_init(self, api_key):
        """Test starting a session when client is not initialized but auto_init is True"""
        # Create client but don't initialize it
        client = Client()
        client.config.api_key = api_key
        client.config.auto_init = True
        
        # Start a session
        with mock.patch.object(client, 'init') as mock_init:
            client.start_session()
            
        # Verify init was called
        mock_init.assert_called_once()
    
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
    
    @mock.patch('agentops.client.Session')
    def test_session_creation_exception_with_fail_safe(self, mock_session, api_key):
        """Test that exceptions during session creation are handled when fail_safe is True"""
        # Mock Session to raise an exception
        mock_session.side_effect = Exception("Test exception")
        
        # Initialize client with fail_safe=True, but don't auto-start session
        client = Client()
        client.init(api_key=api_key, fail_safe=True, auto_start_session=False)
        
        # Start a session - should return None but not raise
        session = client.start_session()
        assert session is None
    
    @mock.patch('agentops.client.Session')
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
    
    @mock.patch('agentops.client.get_default_session')
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
    
    @mock.patch('agentops.client.get_default_session')
    def test_end_session_no_active_session(self, mock_get_default_session):
        """Test ending a session when no session is active"""
        # No active session
        mock_get_default_session.return_value = None
        
        # End the session - should not raise
        client = Client()
        client.end_session("Success", "Test completed")
    
    @mock.patch('agentops.client.get_active_sessions')
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
    
    def test_add_pre_init_warning(self):
        """Test adding pre-init warnings"""
        client = Client()
        
        warning1 = "Warning 1"
        warning2 = "Warning 2"
        
        client.add_pre_init_warning(warning1)
        client.add_pre_init_warning(warning2)
        
        assert client.pre_init_warnings == [warning1, warning2]
    
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