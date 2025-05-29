"""
Unit tests for the AgentOps context manager functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from agentops.context_manager import AgentOpsContextManager, InitializationProxy
from agentops.legacy import Session
from agentops.sdk.core import TraceContext


class TestAgentOpsContextManager:
    """Test the AgentOpsContextManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = Mock()
        self.init_kwargs = {
            "api_key": "test-key",
            "trace_name": "test_trace",
            "auto_start_session": False,
            "default_tags": ["test"],
        }
        self.context_manager = AgentOpsContextManager(self.mock_client, self.init_kwargs)

    @patch("agentops.context_manager.TracingCore")
    def test_enter_with_auto_start_session_true(self, mock_tracing_core):
        """Test __enter__ when auto_start_session=True."""
        # Setup
        mock_session = Mock()
        mock_session.trace_context = Mock()  # Add trace_context attribute
        self.mock_client.init.return_value = mock_session
        self.init_kwargs["auto_start_session"] = True

        # Execute
        result = self.context_manager.__enter__()

        # Verify
        assert result == mock_session
        assert self.context_manager.managed_session == mock_session
        self.mock_client.init.assert_called_once_with(**self.init_kwargs)

    @patch("agentops.context_manager.TracingCore")
    @patch("agentops.context_manager.Session")
    def test_enter_with_auto_start_session_false(self, mock_session_class, mock_tracing_core_class):
        """Test __enter__ when auto_start_session=False."""
        # Setup
        mock_tracing_core = Mock()
        mock_tracing_core_class.get_instance.return_value = mock_tracing_core
        mock_tracing_core.initialized = True

        mock_trace_context = Mock(spec=TraceContext)
        mock_tracing_core.start_trace.return_value = mock_trace_context

        mock_session = Mock()
        mock_session_class.return_value = mock_session

        self.mock_client.init.return_value = None

        # Execute
        result = self.context_manager.__enter__()

        # Verify
        assert result == mock_session
        assert self.context_manager.managed_session == mock_session
        assert self.context_manager._created_trace is True
        mock_tracing_core.start_trace.assert_called_once_with(trace_name="test_trace", tags=["test"])

    @patch("agentops.context_manager.TracingCore")
    def test_enter_tracing_core_not_initialized(self, mock_tracing_core_class):
        """Test __enter__ when TracingCore is not initialized."""
        # Setup
        mock_tracing_core = Mock()
        mock_tracing_core_class.get_instance.return_value = mock_tracing_core
        mock_tracing_core.initialized = False

        self.mock_client.init.return_value = None

        # Execute
        result = self.context_manager.__enter__()

        # Verify
        assert result is None

    @patch("agentops.context_manager.TracingCore")
    def test_exit_success(self, mock_tracing_core_class):
        """Test __exit__ with successful completion."""
        # Setup
        mock_tracing_core = Mock()
        mock_tracing_core_class.get_instance.return_value = mock_tracing_core
        mock_tracing_core.initialized = True

        mock_trace_context = Mock(spec=TraceContext)
        self.context_manager.trace_context = mock_trace_context
        self.context_manager._created_trace = True

        # Execute
        result = self.context_manager.__exit__(None, None, None)

        # Verify
        assert result is False  # Don't suppress exceptions
        mock_tracing_core.end_trace.assert_called_once_with(mock_trace_context, "Success")

    @patch("agentops.context_manager.TracingCore")
    def test_exit_with_exception(self, mock_tracing_core_class):
        """Test __exit__ when an exception occurred."""
        # Setup
        mock_tracing_core = Mock()
        mock_tracing_core_class.get_instance.return_value = mock_tracing_core
        mock_tracing_core.initialized = True

        mock_trace_context = Mock(spec=TraceContext)
        self.context_manager.trace_context = mock_trace_context
        self.context_manager._created_trace = True

        # Execute
        result = self.context_manager.__exit__(ValueError, ValueError("test"), None)

        # Verify
        assert result is False  # Don't suppress exceptions
        mock_tracing_core.end_trace.assert_called_once_with(mock_trace_context, "Error")

    @patch("agentops.context_manager.TracingCore")
    def test_exit_auto_started_session(self, mock_tracing_core_class):
        """Test __exit__ with auto-started session (should not end it)."""
        # Setup
        mock_tracing_core = Mock()
        mock_tracing_core_class.get_instance.return_value = mock_tracing_core
        mock_tracing_core.initialized = True

        mock_session = Mock(spec=Session)
        mock_session.trace_context = Mock()
        self.context_manager.managed_session = mock_session
        self.context_manager._created_trace = False  # Not created by context manager

        # Execute
        result = self.context_manager.__exit__(None, None, None)

        # Verify
        assert result is False
        mock_tracing_core.end_trace.assert_not_called()  # Should not end auto-started session

    def test_getattr_delegation(self):
        """Test that attribute access is delegated to the managed session."""
        # Setup
        mock_session = Mock()
        mock_session.some_method = Mock(return_value="test_result")
        self.context_manager.managed_session = mock_session

        # Execute
        result = self.context_manager.some_method()

        # Verify
        assert result == "test_result"
        mock_session.some_method.assert_called_once()

    def test_getattr_no_session(self):
        """Test that AttributeError is raised when no session is available."""
        # Setup
        self.context_manager.managed_session = None

        # Execute & Verify
        with pytest.raises(AttributeError):
            self.context_manager.some_method()


class TestInitializationProxy:
    """Test the InitializationProxy class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = Mock()
        self.init_kwargs = {"api_key": "test-key"}
        self.proxy = InitializationProxy(self.mock_client, self.init_kwargs)

    def test_ensure_initialized(self):
        """Test that _ensure_initialized calls client.init."""
        # Setup
        mock_result = Mock()
        self.mock_client.init.return_value = mock_result

        # Create a new proxy that hasn't been initialized yet
        proxy = InitializationProxy(self.mock_client, self.init_kwargs)

        # Verify it was initialized during construction
        assert proxy._initialized is True
        assert proxy._result == mock_result
        # Should be called once during construction
        self.mock_client.init.assert_called_with(**self.init_kwargs)

    @patch("agentops.context_manager.AgentOpsContextManager")
    def test_enter_delegates_to_context_manager(self, mock_context_manager_class):
        """Test that __enter__ creates and delegates to AgentOpsContextManager."""
        # Setup
        mock_context_manager = MagicMock()
        mock_context_manager_class.return_value = mock_context_manager
        mock_context_manager.__enter__.return_value = "test_session"

        # Execute
        result = self.proxy.__enter__()

        # Verify
        assert result == "test_session"
        mock_context_manager_class.assert_called_once_with(self.mock_client, self.init_kwargs)
        mock_context_manager.__enter__.assert_called_once()

    def test_exit_delegates_to_context_manager(self):
        """Test that __exit__ delegates to the stored context manager."""
        # Setup
        mock_context_manager = MagicMock()
        mock_context_manager.__exit__.return_value = False
        self.proxy._ctx_manager = mock_context_manager

        # Execute
        result = self.proxy.__exit__(None, None, None)

        # Verify
        assert result is False
        mock_context_manager.__exit__.assert_called_once_with(None, None, None)

    def test_getattr_triggers_initialization(self):
        """Test that attribute access works with initialized proxy."""
        # Setup
        mock_result = Mock()
        mock_result.some_attr = "test_value"
        self.mock_client.init.return_value = mock_result

        # Create a new proxy (which will initialize immediately)
        proxy = InitializationProxy(self.mock_client, self.init_kwargs)

        # Execute
        result = proxy.some_attr

        # Verify
        assert result == "test_value"
        assert proxy._initialized is True
        self.mock_client.init.assert_called_with(**self.init_kwargs)

    def test_bool_evaluation(self):
        """Test boolean evaluation of the proxy."""
        # Setup
        mock_result = Mock()
        self.mock_client.init.return_value = mock_result

        # Execute
        result = bool(self.proxy)

        # Verify
        assert result is True  # Mock objects are truthy
        assert self.proxy._initialized is True

    def test_repr(self):
        """Test string representation of the proxy."""
        # Setup
        mock_result = Mock()
        self.mock_client.init.return_value = mock_result

        # Create a new proxy (which initializes immediately)
        proxy = InitializationProxy(self.mock_client, self.init_kwargs)

        # Test representation after initialization
        repr_result = repr(proxy)
        assert "Mock" in repr_result  # Should show the mock result


class TestIntegration:
    """Integration tests for the context manager functionality."""

    @patch("agentops.context_manager.TracingCore")
    @patch("agentops.context_manager.Session")
    def test_full_context_manager_flow(self, mock_session_class, mock_tracing_core_class):
        """Test the complete flow of using the context manager."""
        # Setup
        mock_client = Mock()
        mock_client.init.return_value = None

        mock_tracing_core = Mock()
        mock_tracing_core_class.get_instance.return_value = mock_tracing_core
        mock_tracing_core.initialized = True

        mock_trace_context = Mock(spec=TraceContext)
        mock_tracing_core.start_trace.return_value = mock_trace_context

        mock_session = Mock(spec=Session)
        mock_session_class.return_value = mock_session

        init_kwargs = {"api_key": "test-key", "trace_name": "integration_test", "auto_start_session": False}

        # Execute
        proxy = InitializationProxy(mock_client, init_kwargs)

        with proxy as session:
            assert session == mock_session
            # Simulate some work
            session.record("test_event")

        # Verify
        # init is called twice: once during proxy construction, once during context manager entry
        assert mock_client.init.call_count == 2
        mock_client.init.assert_called_with(**init_kwargs)
        mock_tracing_core.start_trace.assert_called_once()
        mock_tracing_core.end_trace.assert_called_once_with(mock_trace_context, "Success")
        mock_session.record.assert_called_once_with("test_event")
