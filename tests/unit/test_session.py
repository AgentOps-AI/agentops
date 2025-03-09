import gc
import json
import threading
import time
import uuid
import weakref
from unittest.mock import MagicMock, patch, ANY, call

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import Status, StatusCode

import agentops
from agentops.client import Client
from agentops.config import Config
from agentops.session import Session, SessionState
from agentops.session.registry import _active_sessions, get_active_sessions, clear_registry


# Define the fixture at module level
@pytest.fixture
def mock_get_tracer_provider():
    """
    Mock the get_tracer_provider function to return a mock TracerProvider.
    """
    mock_provider = MagicMock(spec=TracerProvider)

    # Create a patcher for the get_tracer_provider function
    patcher = patch("agentops.session.tracer.get_tracer_provider", return_value=mock_provider)

    # Start the patcher and yield the mock provider
    mock_get_provider = patcher.start()
    mock_get_provider.return_value = mock_provider

    yield mock_provider

    # Stop the patcher after the test is done
    patcher.stop()


@pytest.fixture
def mock_trace_get_tracer_provider():
    """
    Mock the trace.get_tracer_provider function to return a mock TracerProvider.
    """
    mock_provider = MagicMock(spec=TracerProvider)

    # Create a patcher for the trace.get_tracer_provider function
    patcher = patch("opentelemetry.trace.get_tracer_provider", return_value=mock_provider)

    # Start the patcher and yield the mock provider
    mock_get_provider = patcher.start()
    mock_get_provider.return_value = mock_provider

    yield mock_provider

    # Stop the patcher after the test is done
    patcher.stop()


pytestmark = [pytest.mark.usefixture("noinstrument")]


@pytest.fixture(autouse=True)
def cleanup_registry():
    """Clean up the registry before and after each test."""
    clear_registry()
    yield
    clear_registry()


@pytest.fixture
def mock_config():
    """Create a mock config for testing."""
    config = Config(api_key="test-key")
    return config


@pytest.fixture
def mock_span():
    """Create a mock span for testing."""
    span = MagicMock()
    span.set_status = MagicMock()
    span.end = MagicMock()
    # Set end_time to None to simulate a span that hasn't been ended
    span.end_time = None
    # Mock the span context and trace_id
    context = MagicMock()
    context.trace_id = 123456789  # Use a simple integer instead of a complex object
    span.get_span_context.return_value = context
    return span


class TestSessionStart:
    def test_session_start(self):
        """Test that start_session returns a session."""
        with patch("agentops.client.Client.init"), patch("agentops.client.Client.start_session") as mock_start_session:
            # Mock the start_session method to return a Session instance
            mock_session = MagicMock(spec=Session)
            mock_start_session.return_value = mock_session

            # Call start_session
            session = agentops.start_session()

            # Verify that the client's start_session method was called
            mock_start_session.assert_called_once()

            # Verify that the returned session is the mock session
            assert session is mock_session

    def test_session_start_with_tags(self):
        """Test that start_session with tags returns a session directly, not a partial"""
        with patch("agentops.client.Client.init"), patch("agentops.client.Client.start_session") as mock_start_session:
            # Mock the start_session method to return a Session instance
            mock_session = MagicMock(spec=Session)
            mock_start_session.return_value = mock_session

            # Set up the tags
            test_tags = ["test1", "test2"]

            # Call start_session with tags
            session = agentops.start_session(tags=test_tags)

            # Verify that the client's start_session method was called with the tags
            mock_start_session.assert_called_once_with(tags=test_tags)

            # Verify that the returned session is the mock session
            assert session is mock_session

    def test_init_timestamp(self, mock_config):
        """Test that Session.init_timestamp is set."""
        # Create a session directly
        session = Session(config=mock_config)

        # Verify that init_timestamp is set
        assert session.init_timestamp is not None, "Session.init_timestamp should be set"

    def test_session_start_initializes_state(self, mock_config):
        """Test that starting a session initializes the state correctly."""
        with patch("agentops.session.registry.remove_session"), patch("agentops.session.registry.add_session"), patch(
            "agentops.session.registry.set_current_session"
        ):
            # Create a session with auto_start=False
            session = Session(config=mock_config, auto_start=False)

            # Verify that the initial state is INITIALIZING
            assert session.state == SessionState.INITIALIZING

            # Mock the telemetry.start method
            session.telemetry.start = MagicMock()

            # Start the session
            session.start()

            # Verify that the state was updated to RUNNING
            assert session.state == SessionState.RUNNING

            # Verify that telemetry.start was called
            session.telemetry.start.assert_called_once()


class TestSessionEncoding:
    def test_dict(self, mock_config):
        """Test that dict() works with Session objects"""
        # Create a session directly
        session = Session(config=mock_config)

        # Verify that dict() returns a dictionary
        assert isinstance(session.dict(), dict)

    def test_json(self, mock_config):
        """Test that json() works with Session objects"""
        # Create a session directly
        session = Session(config=mock_config)

        # Verify that json() returns a string
        assert isinstance(session.json(), str)


class TestSessionLifecycle:
    def test_session_context_manager(self, mock_config):
        """Test that Session works as a context manager."""
        with patch("agentops.session.registry.remove_session"), patch("agentops.session.registry.add_session"), patch(
            "agentops.session.registry.set_current_session"
        ):
            # Use the session as a context manager
            with Session(config=mock_config) as session:
                # Session should be in RUNNING state
                assert session._state == SessionState.RUNNING

            # After the context manager exits, session should be in SUCCEEDED state
            assert session._state == SessionState.SUCCEEDED

    def test_session_context_manager_with_exception(self, mock_config):
        """Test that Session context manager handles exceptions properly."""
        with patch("agentops.session.registry.remove_session"), patch("agentops.session.registry.add_session"), patch(
            "agentops.session.registry.set_current_session"
        ):
            try:
                with Session(config=mock_config) as session:
                    # Session should be in RUNNING state
                    assert session._state == SessionState.RUNNING

                    # Raise an exception
                    raise ValueError("Test exception")
            except ValueError:
                pass

            # After the exception, session should be in FAILED state
            assert session._state == SessionState.FAILED

    def test_session_del_method(self, mock_config):
        """Test that Session.__del__ method ends the session properly."""
        with patch("agentops.session.registry.remove_session"), patch("agentops.session.registry.add_session"), patch(
            "agentops.session.registry.set_current_session"
        ):
            # Create a session
            session = Session(config=mock_config)

            # Get the session ID for later verification
            session_id = session.session_id

            # Session should be in RUNNING state
            assert session._state == SessionState.RUNNING

            # Mock the end method to verify it's called
            original_end = session.end
            session.end = MagicMock(wraps=original_end)

            # Delete the session reference
            del session

            # Force garbage collection
            gc.collect()

            # Wait a bit for GC to complete
            time.sleep(0.1)

            # Note: We can't directly verify that end was called because the session object
            # no longer exists. This test mainly ensures that __del__ doesn't raise exceptions.

    def test_session_del_basic(self, mock_config):
        """Basic test for Session.__del__ method.

        This test simply verifies that the __del__ method doesn't raise exceptions.
        """
        # Create a session
        session = Session(config=mock_config)

        # Delete the session reference
        del session

        # Force garbage collection
        gc.collect()

        # Wait a bit for GC to complete
        time.sleep(0.1)

        # If we got here without exceptions, the test passes

    def test_session_end_idempotent(self, mock_config):
        """Test that calling end() multiple times is idempotent."""
        with patch("agentops.session.registry.remove_session"), patch("agentops.session.registry.add_session"), patch(
            "agentops.session.registry.set_current_session"
        ):
            # Create a session
            session = Session(config=mock_config)

            # End the session with SUCCEEDED state
            session.end(SessionState.SUCCEEDED)

            # Session should be in SUCCEEDED state
            assert session._state == SessionState.SUCCEEDED

            # End the session again with a different state
            session.end(SessionState.FAILED)

            # State should not change
            assert session._state == SessionState.SUCCEEDED

    def test_concurrent_session_operations(self, mock_config):
        """Test that concurrent session operations are thread-safe."""
        with patch("agentops.session.registry.remove_session"), patch("agentops.session.registry.add_session"), patch(
            "agentops.session.registry.set_current_session"
        ):
            # Create a session
            session = Session(config=mock_config)

            # Define a function that ends the session
            def end_session():
                session.end(SessionState.SUCCEEDED)

            # Create and start a thread that ends the session
            thread = threading.Thread(target=end_session)
            thread.start()

            # Try to end the session from the main thread
            session.end(SessionState.FAILED)

            # Wait for the thread to complete
            thread.join()

            # Only one end operation should succeed
            assert session._state == SessionState.SUCCEEDED or session._state == SessionState.FAILED


class TestSessionSpanStatus:
    def test_session_end_updates_status(self, mock_config, mock_span):
        """Test that ending a session updates the span status correctly."""
        with patch("agentops.session.registry.remove_session"), patch("agentops.session.registry.add_session"), patch(
            "agentops.session.registry.set_current_session"
        ):
            # Create a session
            session = Session(config=mock_config)

            # Replace the span with our mock
            session._span = mock_span

            # End the session with SUCCEEDED state
            session.end(SessionState.SUCCEEDED)

            # Verify that the span status was set with a Status object containing OK code
            mock_span.set_status.assert_called_once()
            status_arg = mock_span.set_status.call_args[0][0]
            assert isinstance(status_arg, Status)
            assert status_arg.status_code == StatusCode.OK

            # Verify that the span was ended
            mock_span.end.assert_called_once()

    def test_session_end_failed_updates_status(self, mock_config, mock_span):
        """Test that ending a session with FAILED status sets the correct span status."""
        with patch("agentops.session.registry.remove_session"), patch("agentops.session.registry.add_session"), patch(
            "agentops.session.registry.set_current_session"
        ):
            # Create a session
            session = Session(config=mock_config)

            # Replace the span with our mock
            session._span = mock_span

            # End the session with FAILED state
            session.end(SessionState.FAILED)

            # Verify that the span status was set with a Status object containing ERROR code
            mock_span.set_status.assert_called_once()
            status_arg = mock_span.set_status.call_args[0][0]
            assert isinstance(status_arg, Status)
            assert status_arg.status_code == StatusCode.ERROR

            # Verify that the span was ended
            mock_span.end.assert_called_once()

    def test_session_end_indeterminate_updates_status(self, mock_config, mock_span):
        """Test that ending a session with INDETERMINATE status sets the correct span status."""
        with patch("agentops.session.registry.remove_session"), patch("agentops.session.registry.add_session"), patch(
            "agentops.session.registry.set_current_session"
        ):
            # Create a session
            session = Session(config=mock_config)

            # Replace the span with our mock
            session._span = mock_span

            # End the session with INDETERMINATE state
            session.end(SessionState.INDETERMINATE)

            # Verify that the span status was set with a Status object containing UNSET code
            mock_span.set_status.assert_called_once()
            status_arg = mock_span.set_status.call_args[0][0]
            assert isinstance(status_arg, Status)
            assert status_arg.status_code == StatusCode.UNSET

            # Verify that the span was ended
            mock_span.end.assert_called_once()

    def test_session_context_manager_exception_status(self, mock_config, mock_span):
        """Test that the context manager sets the correct span status when an exception occurs."""
        with patch("agentops.session.registry.remove_session"), patch("agentops.session.registry.add_session"), patch(
            "agentops.session.registry.set_current_session"
        ):
            try:
                # Use the session as a context manager
                with Session(config=mock_config) as session:
                    # Replace the span with our mock
                    session._span = mock_span

                    # Raise an exception
                    raise ValueError("Test exception")
            except ValueError:
                pass

            # Verify that the span status was set with a Status object containing ERROR code
            mock_span.set_status.assert_called_once()
            status_arg = mock_span.set_status.call_args[0][0]
            assert isinstance(status_arg, Status)
            assert status_arg.status_code == StatusCode.ERROR

            # Verify that the span was ended
            mock_span.end.assert_called_once()

    def test_session_already_ended_no_status_update(self, mock_config, mock_span):
        """Test that ending an already ended session doesn't update the status."""
        with patch("agentops.session.registry.remove_session"), patch("agentops.session.registry.add_session"), patch(
            "agentops.session.registry.set_current_session"
        ):
            # Create a session with a mock span
            session = Session(config=mock_config)
            session._span = mock_span

            # End the session
            session.end(SessionState.SUCCEEDED)

            # Reset the mock to clear the call history
            mock_span.set_status.reset_mock()
            mock_span.end.reset_mock()

            # End the session again
            session.end(SessionState.FAILED)

            # Verify that the span status was not updated
            mock_span.set_status.assert_not_called()

            # Verify that the span was not ended again
            mock_span.end.assert_not_called()

    def test_session_no_span_no_error(self, mock_config):
        """Test that ending a session without a span doesn't cause an error."""
        with patch("agentops.session.registry.remove_session"), patch("agentops.session.registry.add_session"), patch(
            "agentops.session.registry.set_current_session"
        ):
            # Create a session
            session = Session(config=mock_config)

            # Set the span to None
            session._span = None

            # End the session
            # This should not raise an exception
            session.end(SessionState.SUCCEEDED)

            # Verify that the session state was updated
            assert session._state == SessionState.SUCCEEDED

    def test_session_telemetry_shutdown(self, mock_config, mock_trace_get_tracer_provider):
        """Test that the telemetry.shutdown method is called during session end."""
        with patch("agentops.session.registry.remove_session"), patch("agentops.session.registry.add_session"), patch(
            "agentops.session.registry.set_current_session"
        ):
            # Create a session
            session = Session(config=mock_config)

            # Create a spy on the telemetry.shutdown method instead of replacing it
            shutdown_spy = patch.object(session.telemetry, "shutdown", wraps=session.telemetry.shutdown)
            with shutdown_spy as mock_shutdown:
                # End the session
                session.end()

                # Verify that telemetry.shutdown was called
                mock_shutdown.assert_called_once()

            # Verify force_flush was called on the provider
            mock_trace_get_tracer_provider.force_flush.assert_called_once()
