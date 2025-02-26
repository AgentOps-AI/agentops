import uuid
import pytest
from unittest import mock
import json

import agentops
from agentops.client import Client
from agentops._singleton import ao_instances, clear_singletons
from agentops.exceptions import AgentOpsClientNotInitializedException, NoApiKeyException, NoSessionException
from agentops.instrumentation import instrument_all, uninstrument_all
from agentops.session import Session
from agentops.session.state import SessionState
from opentelemetry.sdk.trace import SpanProcessor
from opentelemetry.sdk.trace.export import SpanExporter


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
        assert any(
            call.url.endswith("/v2/create_session") 
            for call in mock_req.request_history
        )
    
    def test_client_init_no_auto_start_session(self, api_key, mock_req):
        """Test that auto_start_session=False doesn't create a session during init"""
        # Initialize client with auto_start_session=False
        client = Client()
        returned_session = client.init(api_key=api_key, auto_start_session=False)
        
        # Verify no session was returned
        assert returned_session is None
        
        # Verify no API call was made to create a session
        assert not any(
            call.url.endswith("/v2/create_session") 
            for call in mock_req.request_history
        )
    
    @mock.patch('agentops.client.get_default_session')
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
    
    @mock.patch('agentops.client.get_default_session')
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
    
    @mock.patch('agentops.client.get_active_sessions')
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

    @mock.patch('agentops.telemetry.session.OTLPSpanExporter')
    @mock.patch('agentops.telemetry.session.SimpleSpanProcessor')
    def test_init_with_custom_exporter(self, mock_simple_processor, mock_otlp_exporter, api_key):
        """Test that a custom exporter is used when provided to init()"""
        # Create a mock exporter
        mock_exporter = mock.MagicMock(spec=SpanExporter)
        
        # Initialize with the custom exporter using the public API
        session = agentops.init(
            api_key=api_key,
            exporter=mock_exporter,
            auto_start_session=True
        )
        
        # Verify the session was created
        assert session is not None
        assert isinstance(session, Session)
        
        # Verify that SimpleSpanProcessor was created with our mock exporter
        # and not with the default OTLPSpanExporter
        mock_simple_processor.assert_called_with(mock_exporter)
        mock_otlp_exporter.assert_not_called()
    
    @mock.patch('agentops.telemetry.session.get_tracer_provider')
    def test_init_with_custom_processor(self, mock_get_tracer_provider, api_key):
        """Test that a custom processor is used when provided to init()"""
        # Create a mock processor and provider
        mock_processor = mock.MagicMock(spec=SpanProcessor)
        mock_provider = mock.MagicMock()
        mock_get_tracer_provider.return_value = mock_provider
        
        # Initialize with the custom processor using the public API
        session = agentops.init(
            api_key=api_key,
            processor=mock_processor,
            auto_start_session=True
        )
        
        # Verify the session was created
        assert session is not None
        assert isinstance(session, Session)
        
        # Verify that our mock processor was added to the provider
        mock_provider.add_span_processor.assert_called_with(mock_processor)
    
    @mock.patch('agentops.telemetry.session.get_tracer_provider')
    @mock.patch('agentops.telemetry.session.SimpleSpanProcessor')
    def test_processor_takes_precedence_over_exporter(self, 
                                                      mock_simple_processor, 
                                                      mock_get_tracer_provider, 
                                                      api_key):
        """Test that processor takes precedence over exporter when both are provided"""
        # Create mock processor, exporter, and provider
        mock_processor = mock.MagicMock(spec=SpanProcessor)
        mock_exporter = mock.MagicMock(spec=SpanExporter)
        mock_provider = mock.MagicMock()
        mock_get_tracer_provider.return_value = mock_provider
        
        # Initialize with both processor and exporter using the public API
        session = agentops.init(
            api_key=api_key,
            processor=mock_processor,
            exporter=mock_exporter,
            auto_start_session=True
        )
        
        # Verify the session was created
        assert session is not None
        assert isinstance(session, Session)
        
        # Verify that our mock processor was added to the provider
        mock_provider.add_span_processor.assert_called_with(mock_processor)
        
        # Verify that SimpleSpanProcessor was NOT created with our mock exporter
        mock_simple_processor.assert_not_called()
    
    def test_exporter_and_processor_in_config(self, api_key):
        """Test that exporter and processor are stored in the config"""
        # Create mock processor and exporter
        mock_processor = mock.MagicMock(spec=SpanProcessor)
        mock_exporter = mock.MagicMock(spec=SpanExporter)
        
        # Initialize with both processor and exporter using the public API
        agentops.init(
            api_key=api_key,
            processor=mock_processor,
            exporter=mock_exporter,
            auto_start_session=False
        )
        
        # Get the client to check its config
        client = agentops.get_client()
        
        # Verify that the processor and exporter are stored in the config
        assert client.config.processor is mock_processor
        assert client.config.exporter is mock_exporter 

    @mock.patch('agentops.telemetry.session.get_tracer_provider')
    def test_telemetry_uses_custom_components(self, mock_get_tracer_provider, api_key):
        """Test that SessionTelemetry actually uses the custom components for recording spans"""
        # Create mock objects
        mock_tracer = mock.MagicMock()
        mock_provider = mock.MagicMock()
        mock_provider.get_tracer.return_value = mock_tracer
        mock_get_tracer_provider.return_value = mock_provider
        
        # Create a custom processor
        mock_processor = mock.MagicMock(spec=SpanProcessor)
        
        # Initialize with custom processor
        session = agentops.init(
            api_key=api_key,
            processor=mock_processor,
            auto_start_session=True
        )
        
        # Verify the session was created
        assert session is not None
        assert isinstance(session, Session)
        
        # Verify the processor was added to the provider
        mock_provider.add_span_processor.assert_called_with(mock_processor)
        
        # Verify the session has telemetry
        assert hasattr(session, "telemetry")
        
        # Verify that tracer from provider is used
        assert session.telemetry.tracer is mock_tracer
        
        # Verify the provider is properly set up with our processor
        mock_provider.get_tracer.assert_called_with("agentops.session") 