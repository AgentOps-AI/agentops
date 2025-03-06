"""Unit tests for session termination functionality.

This file contains all unit tests related to session termination, including:
- Session.__del__ method implementation
- SessionTracer.__del__ method implementation
- SessionTracer.shutdown method implementation
- Proper cleanup during garbage collection
- Error handling during termination
- Thread safety and timeout handling
"""

import gc
import threading
import time
import unittest
from unittest.mock import patch, MagicMock

from agentops.config import default_config
from agentops.session.state import SessionState
from agentops.session.session import Session
from agentops.session.tracer import SessionTracer, _session_tracers
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

    # =========================================================================
    # Session.__del__ method tests
    # =========================================================================

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

    def test_session_del_with_multiple_spans(self):
        """Test that __del__ properly ends all spans in a session with multiple spans."""
        # Create a mock session with multiple spans
        with patch("agentops.session.session.Session.end") as mock_end:
            session = MagicMock()
            session._state = SessionState.RUNNING
            session.session_id = "test-session-id"

            # Create mock spans
            mock_span1 = MagicMock()
            mock_span1.end_time = None  # Span has not ended yet
            mock_span2 = MagicMock()
            mock_span2.end_time = None  # Span has not ended yet

            # Set up spans property to return multiple spans
            session.spans = [mock_span1, mock_span2]

            # Call the __del__ method directly
            Session.__del__(session)

            # Check that end() was called
            session.end.assert_called_once()

    def test_span_processor_flush_during_del(self):
        """Test that span processors are flushed during __del__."""
        # Create a real session with mocked components
        with patch("agentops.session.tracer.trace") as mock_trace:
            # Create a mock tracer provider
            mock_provider = MagicMock(spec=TracerProvider)
            mock_trace.get_tracer_provider.return_value = mock_provider

            # Create a session
            session = Session(config=default_config())

            # Let the session go out of scope
            del session

            # Force garbage collection
            gc.collect()

            # Wait a bit for GC to complete
            time.sleep(0.5)

            # Check that force_flush was called on the provider
            mock_provider.force_flush.assert_called_with(timeout_millis=5000)

    def test_tracer_provider_shutdown_during_del(self):
        """Test that the tracer is properly cleaned up during __del__."""
        # Create a session
        session = Session(config=default_config())
        session_id = str(session.session_id)

        # Verify the session is in the registry
        self.assertIn(session_id, _session_tracers)

        # Let the session go out of scope
        del session

        # Force garbage collection
        gc.collect()

        # Wait a bit for GC to complete
        time.sleep(0.5)

        # Verify the session is no longer in the registry, which means shutdown was called
        self.assertNotIn(session_id, _session_tracers)

    def test_session_del_with_exception_in_end(self):
        """Test that __del__ handles exceptions in end() gracefully."""
        # Create a session with end() that raises an exception
        with patch.object(Session, "end", side_effect=Exception("Test exception in end()")):
            # Create a session
            session = Session(config=default_config())
            session_id = str(session.session_id)

            # Let the session go out of scope
            del session

            # Force garbage collection
            gc.collect()

            # Wait a bit for GC to complete
            time.sleep(0.5)

            # Check that logger.warning was called with the expected message
            warning_calls = [
                call
                for call in self.mock_logger.warning.call_args_list
                if f"Error during Session.__del__ for session {session_id}" in str(call)
            ]
            self.assertTrue(
                len(warning_calls) >= 1,
                f"Expected warning log with session ID {session_id}, but got {self.mock_logger.warning.call_args_list}",
            )

    def test_session_del_with_timeout_in_flush(self):
        """Test that __del__ handles timeouts in force_flush gracefully."""
        # Create a real session with mocked components
        with patch("agentops.session.tracer.trace") as mock_trace:
            # Create a mock tracer provider with force_flush that times out
            mock_provider = MagicMock(spec=TracerProvider)
            mock_provider.force_flush.side_effect = TimeoutError("Flush timeout")
            mock_trace.get_tracer_provider.return_value = mock_provider

            # Create a session
            session = Session(config=default_config())

            # Let the session go out of scope
            del session

            # Force garbage collection
            gc.collect()

            # Wait a bit for GC to complete
            time.sleep(0.5)

            # Check that force_flush was called on the provider
            mock_provider.force_flush.assert_called_with(timeout_millis=5000)

            # Check that the warning was logged
            warning_calls = [
                call
                for call in self.mock_tracer_logger.warning.call_args_list
                if "Error during span processor flush" in str(call)
            ]
            self.assertTrue(
                len(warning_calls) >= 1,
                f"Expected warning log about flush error, but got {self.mock_tracer_logger.warning.call_args_list}",
            )

    def test_session_del_with_circular_reference(self):
        """Test that __del__ works correctly with circular references."""
        # Create a session with a circular reference
        with patch.object(Session, "__del__", autospec=True) as mock_del:
            # Create a session
            session = Session(config=default_config())

            # Create a circular reference
            session._circular_ref = session

            # Let the session go out of scope
            del session

            # Force garbage collection
            gc.collect()

            # Wait a bit for GC to complete
            time.sleep(0.5)

            # Check that __del__ was called
            mock_del.assert_called()

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

    def test_real_session_cleanup_with_gc(self):
        """Integration test for real session cleanup during garbage collection."""
        # Create a real session with mocked components
        with patch("agentops.session.tracer.trace") as mock_trace, patch.object(
            Session, "end", wraps=Session.end
        ) as mock_end:
            # Create a mock tracer provider
            mock_provider = MagicMock(spec=TracerProvider)
            mock_trace.get_tracer_provider.return_value = mock_provider

            # Create a session
            session = Session(config=default_config())
            session_id = str(session.session_id)

            # Let the session go out of scope
            del session

            # Force garbage collection
            gc.collect()

            # Wait a bit for GC to complete
            time.sleep(0.5)

            # Check that end() was called
            self.assertTrue(
                mock_end.call_count >= 1,
                f"Expected end to be called at least once, but was called {mock_end.call_count} times",
            )

            # Check that force_flush was called on the provider
            mock_provider.force_flush.assert_called_with(timeout_millis=5000)

    # =========================================================================
    # SessionTracer.shutdown method tests
    # =========================================================================

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
        tracer._is_ended = False

        # Call the __del__ method directly
        SessionTracer.__del__(tracer)

        # Check that shutdown was called
        tracer.shutdown.assert_called_once()

    def test_shutdown_with_timeout(self):
        """Test that shutdown handles timeouts gracefully."""
        # Create a mock session
        mock_session = MagicMock()
        mock_session.session_id = "test-session-id"

        # Create a mock span
        mock_span = MagicMock()
        mock_span.end_time = None  # Span has not ended yet
        mock_session._span = mock_span

        # Create a mock for the context module
        with patch("agentops.session.tracer.context") as mock_context, patch(
            "agentops.session.tracer.trace"
        ) as mock_trace:
            # Create a mock tracer provider that times out during force_flush
            mock_provider = MagicMock(spec=TracerProvider)
            mock_provider.force_flush.side_effect = TimeoutError("Flush timeout")
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

            # Check that force_flush was called on the provider with the timeout
            mock_provider.force_flush.assert_called_once_with(timeout_millis=5000)

            # Check that the warning was logged
            self.mock_tracer_logger.warning.assert_called_once()

            # Check that _is_ended was set to True despite the timeout
            self.assertTrue(mock_tracer._is_ended)

    def test_shutdown_thread_safety(self):
        """Test that shutdown is thread-safe."""
        # Create a mock session
        mock_session = MagicMock()
        mock_session.session_id = "test-session-id"

        # Create a mock span
        mock_span = MagicMock()
        mock_span.end_time = None  # Span has not ended yet
        mock_session._span = mock_span

        # Create a mock for the context module
        with patch("agentops.session.tracer.context") as mock_context, patch(
            "agentops.session.tracer.trace"
        ) as mock_trace:
            # Create a mock tracer provider
            mock_provider = MagicMock(spec=TracerProvider)
            mock_trace.get_tracer_provider.return_value = mock_provider

            # Create a real lock for thread safety testing
            shutdown_lock = threading.Lock()

            # Create a mock tracer with a real lock
            mock_tracer = MagicMock()
            mock_tracer.session = mock_session
            mock_tracer._is_ended = False
            mock_tracer._token = "mock-token"
            mock_tracer.session_id = "test-session-id"
            mock_tracer._shutdown_lock = shutdown_lock

            # Define a function to call shutdown from multiple threads
            def call_shutdown():
                SessionTracer.shutdown(mock_tracer)

            # Create and start multiple threads
            threads = []
            for _ in range(5):
                thread = threading.Thread(target=call_shutdown)
                threads.append(thread)
                thread.start()

            # Wait for all threads to complete
            for thread in threads:
                thread.join()

            # Check that context.detach was called exactly once
            mock_context.detach.assert_called_once_with("mock-token")

            # Check that the span was ended exactly once
            mock_span.end.assert_called_once()

            # Check that force_flush was called exactly once
            mock_provider.force_flush.assert_called_once_with(timeout_millis=5000)

            # Check that _is_ended was set to True
            self.assertTrue(mock_tracer._is_ended)

    def test_shutdown_with_already_ended_span(self):
        """Test that shutdown handles already ended spans gracefully."""
        # Create a mock session
        mock_session = MagicMock()
        mock_session.session_id = "test-session-id"

        # Create a mock span that has already been ended
        mock_span = MagicMock()
        mock_span.end_time = 123456789  # Span has already ended
        mock_session._span = mock_span

        # Create a mock for the context module
        with patch("agentops.session.tracer.context") as mock_context, patch(
            "agentops.session.tracer.trace"
        ) as mock_trace:
            # Create a mock tracer provider
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

            # Check that the span was not ended again
            mock_span.end.assert_not_called()

            # Check that force_flush was called on the provider
            mock_provider.force_flush.assert_called_once_with(timeout_millis=5000)

            # Check that _is_ended was set to True
            self.assertTrue(mock_tracer._is_ended)

    def test_shutdown_with_no_span(self):
        """Test that shutdown handles sessions with no span gracefully."""
        # Create a mock session with no span
        mock_session = MagicMock()
        mock_session.session_id = "test-session-id"
        mock_session._span = None

        # Create a mock for the context module
        with patch("agentops.session.tracer.context") as mock_context, patch(
            "agentops.session.tracer.trace"
        ) as mock_trace:
            # Create a mock tracer provider
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

            # Check that force_flush was called on the provider
            mock_provider.force_flush.assert_called_once_with(timeout_millis=5000)

            # Check that _is_ended was set to True
            self.assertTrue(mock_tracer._is_ended)

    def test_shutdown_already_ended_tracer(self):
        """Test that shutdown is idempotent and can be called multiple times."""
        # Create a mock session
        mock_session = MagicMock()
        mock_session.session_id = "test-session-id"

        # Create a mock span
        mock_span = MagicMock()
        mock_span.end_time = None  # Span has not ended yet
        mock_session._span = mock_span

        # Create a mock for the context module
        with patch("agentops.session.tracer.context") as mock_context, patch(
            "agentops.session.tracer.trace"
        ) as mock_trace:
            # Create a mock tracer provider
            mock_provider = MagicMock(spec=TracerProvider)
            mock_trace.get_tracer_provider.return_value = mock_provider

            # Create a mock tracer that has already been ended
            mock_tracer = MagicMock()
            mock_tracer.session = mock_session
            mock_tracer._is_ended = True  # Already ended
            mock_tracer._token = "mock-token"
            mock_tracer.session_id = "test-session-id"

            # Create a mock lock
            mock_lock = MagicMock()
            mock_lock.__enter__ = MagicMock(return_value=None)
            mock_lock.__exit__ = MagicMock(return_value=None)
            mock_tracer._shutdown_lock = mock_lock

            # Call the shutdown method directly
            SessionTracer.shutdown(mock_tracer)

            # Check that context.detach was not called
            mock_context.detach.assert_not_called()

            # Check that the span was not ended
            mock_span.end.assert_not_called()

            # Check that force_flush was not called on the provider
            mock_provider.force_flush.assert_not_called()

            # Check that _is_ended is still True
            self.assertTrue(mock_tracer._is_ended)

    # =========================================================================
    # Session.end method tests
    # =========================================================================

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


if __name__ == "__main__":
    unittest.main()
