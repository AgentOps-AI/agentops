"""Unit tests for session termination functionality.

This file contains all unit tests related to session termination, including:
- Session.__del__ method implementation
- SessionTracer.__del__ method implementation
- Proper cleanup during garbage collection
- Error handling during termination
"""

import gc
import time
import unittest
from unittest.mock import patch, MagicMock, call

from agentops.config import default_config
from agentops.session.state import SessionState
from agentops.session.session import Session
from agentops.session.tracer import SessionTracer
from opentelemetry.sdk.trace import TracerProvider


class TestSessionTermination(unittest.TestCase):
    """Unit tests for session termination functionality."""

    def setUp(self):
        """Set up test environment."""
        # Patch the logger to prevent actual logging during tests
        self.logger_patcher = patch("agentops.session.session.logger")
        self.mock_logger = self.logger_patcher.start()

        # Patch the tracer logger
        self.tracer_logger_patcher = patch("agentops.session.tracer.logger")
        self.mock_tracer_logger = self.tracer_logger_patcher.start()

    def tearDown(self):
        """Clean up after tests."""
        self.logger_patcher.stop()
        self.tracer_logger_patcher.stop()

        # Force garbage collection
        gc.collect()

    @patch("agentops.session.session.Session.end")
    def test_session_del_calls_end(self, mock_end):
        """Test that __del__ calls end() when session is still running."""
        # Create a mock session with the necessary attributes
        session = MagicMock()
        session._state = SessionState.RUNNING
        session.session_id = "test-session-id"

        # Call the __del__ method directly
        Session.__del__(session)

        # Check that logger.info was called with the expected message
        self.mock_logger.info.assert_called_once()

        # Check that end() was called
        session.end.assert_called_once()

    @patch("agentops.session.session.Session.end")
    def test_session_del_handles_exceptions(self, mock_end):
        """Test that __del__ handles exceptions gracefully."""
        # Create a mock session with the necessary attributes
        session = MagicMock()
        session._state = SessionState.RUNNING
        session.session_id = "test-session-id"
        session.end.side_effect = Exception("Test exception")

        # Call the __del__ method directly
        Session.__del__(session)

        # Check that logger.warning was called with the expected message
        self.mock_logger.warning.assert_called_once()

    @patch("agentops.session.session.Session.end")
    def test_session_del_with_already_ended_session(self, mock_end):
        """Test that __del__ doesn't call end() when session is already ended."""
        # Create a mock session with the necessary attributes
        session = MagicMock()
        session._state = SessionState.SUCCEEDED
        session.session_id = "test-session-id"

        # Call the __del__ method directly
        Session.__del__(session)

        # Check that end() was not called again
        session.end.assert_not_called()

    def test_tracer_shutdown_sequence(self):
        """Test that the tracer shutdown sequence is correct."""
        # Create a mock session with a span
        mock_session = MagicMock()
        mock_session.session_id = "test-session-id"
        mock_span = MagicMock()
        mock_span.end_time = None  # Span has not ended yet
        mock_session._span = mock_span

        # Create a mock for the context module
        with patch("agentops.session.tracer.context") as mock_context, patch(
            "agentops.session.tracer.trace"
        ) as mock_trace:
            # Create a mock tracer provider that is an instance of TracerProvider
            mock_provider = MagicMock(spec=TracerProvider)
            mock_trace.get_tracer_provider.return_value = mock_provider

            # Create a mock tracer
            mock_tracer = MagicMock()
            mock_tracer.session = mock_session
            mock_tracer._is_ended = False
            mock_tracer._token = "mock-token"
            mock_tracer.session_id = "test-session-id"

            # Create a mock lock
            mock_lock = MagicMock()
            mock_lock.__enter__ = MagicMock(return_value=None)
            mock_lock.__exit__ = MagicMock(return_value=None)
            mock_tracer._shutdown_lock = mock_lock

            # Call the shutdown method directly
            SessionTracer.shutdown(mock_tracer)

            # Check that context.detach was called with the token
            mock_context.detach.assert_called_once_with("mock-token")

            # Check that the span was ended
            mock_span.end.assert_called_once()

            # Check that force_flush was called on the provider
            # We no longer call shutdown() on the provider in SessionTracer.shutdown()
            mock_provider.force_flush.assert_called_once_with(timeout_millis=5000)

            # Check that _is_ended was set to True
            self.assertTrue(mock_tracer._is_ended)

    @patch("agentops.session.tracer.SessionTracer.shutdown")
    def test_session_tracer_del(self, mock_shutdown):
        """Test that SessionTracer.__del__ calls shutdown."""
        # Create a mock tracer with the necessary attributes
        tracer = MagicMock()
        tracer.session_id = "test-session-id"

        # Call the __del__ method directly
        SessionTracer.__del__(tracer)

        # Check that shutdown was called
        tracer.shutdown.assert_called_once()

    def test_end_sets_session_state(self):
        """Test that the end() method sets the session state to SUCCEEDED."""
        # Create a mock session with the necessary attributes
        session = MagicMock()
        session._state = SessionState.RUNNING
        session._lock = MagicMock()
        session._lock.__enter__ = MagicMock(return_value=None)
        session._lock.__exit__ = MagicMock(return_value=None)
        session.telemetry = MagicMock()

        # Call the end method directly
        Session.end(session)

        # Verify that telemetry.shutdown was called
        session.telemetry.shutdown.assert_called_once()

        # Verify that the session state was set to SUCCEEDED
        self.assertEqual(session._state, SessionState.SUCCEEDED)

    def test_session_del_with_gc(self):
        """Test that Session.__del__ is called during garbage collection."""
        # Patch the __del__ method to track calls
        with patch.object(Session, "__del__", autospec=True) as mock_del:
            # Create a session
            session = Session(config=default_config())
            session_id = str(session.session_id)

            # Let the session go out of scope
            del session

            # Trigger garbage collection
            gc.collect()

            # Wait a bit for GC to complete
            time.sleep(0.5)

            # Check that __del__ was called at least once
            # Note: This might be flaky as GC timing is not deterministic
            mock_del.assert_called()


if __name__ == "__main__":
    unittest.main()
