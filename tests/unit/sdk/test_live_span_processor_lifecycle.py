"""
Tests for LiveSpanProcessor lifecycle management improvements.

This module tests the enhanced shutdown functionality that was added to prevent
resource leaks by properly managing thread lifecycle with timeouts and error handling.
"""

import threading
import time
from unittest.mock import MagicMock, patch, call

from agentops.sdk.processors import LiveSpanProcessor


class TestLiveSpanProcessorShutdown:
    """Tests for the enhanced LiveSpanProcessor shutdown functionality."""

    def test_shutdown_normal_thread_termination(self):
        """Test shutdown with normal thread termination."""
        # Create a mock exporter
        mock_exporter = MagicMock()

        # Create processor
        processor = LiveSpanProcessor(mock_exporter)

        # Verify thread is running
        assert processor._export_thread.is_alive()

        # Shutdown
        processor.shutdown()

        # Verify thread stopped
        assert not processor._export_thread.is_alive()

        # Verify exporter shutdown was called
        mock_exporter.shutdown.assert_called_once()

    @patch("agentops.sdk.processors.logger")
    def test_shutdown_with_thread_timeout(self, mock_logger):
        """Test shutdown when thread doesn't terminate within timeout."""
        # Create a mock exporter
        mock_exporter = MagicMock()

        # Create processor
        processor = LiveSpanProcessor(mock_exporter)

        # Mock the thread to simulate it not terminating
        with patch.object(processor._export_thread, "join") as mock_join:
            with patch.object(processor._export_thread, "is_alive", return_value=True):
                # Shutdown
                processor.shutdown()

                # Verify join was called with timeout
                mock_join.assert_called_once_with(timeout=5.0)

                # Verify warning was logged
                mock_logger.warning.assert_called_once_with(
                    "Export thread did not shut down within timeout, continuing shutdown"
                )

        # Verify exporter shutdown was still called
        mock_exporter.shutdown.assert_called_once()

    @patch("agentops.sdk.processors.logger")
    def test_shutdown_thread_join_exception(self, mock_logger):
        """Test shutdown when thread.join() raises an exception."""
        # Create a mock exporter
        mock_exporter = MagicMock()

        # Create processor
        processor = LiveSpanProcessor(mock_exporter)

        # Mock the thread join to raise an exception
        with patch.object(processor._export_thread, "join", side_effect=Exception("Join failed")):
            # Shutdown should not raise exception
            processor.shutdown()

            # Verify error was logged
            mock_logger.error.assert_called_once_with("Error during thread shutdown: Join failed")

        # Verify exporter shutdown was still called
        mock_exporter.shutdown.assert_called_once()

    @patch("agentops.sdk.processors.logger")
    def test_shutdown_exporter_shutdown_exception(self, mock_logger):
        """Test shutdown when exporter.shutdown() raises an exception."""
        # Create a mock exporter that raises exception on shutdown
        mock_exporter = MagicMock()
        mock_exporter.shutdown.side_effect = Exception("Exporter shutdown failed")

        # Create processor
        processor = LiveSpanProcessor(mock_exporter)

        # Shutdown should not raise exception
        processor.shutdown()

        # Verify error was logged
        mock_logger.error.assert_called_once_with("Error shutting down span exporter: Exporter shutdown failed")

        # Verify exporter shutdown was attempted
        mock_exporter.shutdown.assert_called_once()

    @patch("agentops.sdk.processors.logger")
    def test_shutdown_both_thread_and_exporter_exceptions(self, mock_logger):
        """Test shutdown when both thread join and exporter shutdown raise exceptions."""
        # Create a mock exporter that raises exception on shutdown
        mock_exporter = MagicMock()
        mock_exporter.shutdown.side_effect = Exception("Exporter shutdown failed")

        # Create processor
        processor = LiveSpanProcessor(mock_exporter)

        # Mock the thread join to raise an exception
        with patch.object(processor._export_thread, "join", side_effect=Exception("Join failed")):
            # Shutdown should not raise exception
            processor.shutdown()

            # Verify both errors were logged
            expected_calls = [
                call("Error during thread shutdown: Join failed"),
                call("Error shutting down span exporter: Exporter shutdown failed"),
            ]
            mock_logger.error.assert_has_calls(expected_calls)

        # Verify exporter shutdown was attempted
        mock_exporter.shutdown.assert_called_once()

    def test_shutdown_thread_already_stopped(self):
        """Test shutdown when thread is already stopped."""
        # Create a mock exporter
        mock_exporter = MagicMock()

        # Create processor
        processor = LiveSpanProcessor(mock_exporter)

        # Stop the thread manually first
        processor._stop_event.set()
        processor._export_thread.join()

        # Verify thread is stopped
        assert not processor._export_thread.is_alive()

        # Shutdown should still work
        processor.shutdown()

        # Verify exporter shutdown was called
        mock_exporter.shutdown.assert_called_once()

    def test_shutdown_multiple_calls(self):
        """Test that multiple shutdown calls don't cause issues."""
        # Create a mock exporter
        mock_exporter = MagicMock()

        # Create processor
        processor = LiveSpanProcessor(mock_exporter)

        # Call shutdown multiple times
        processor.shutdown()
        processor.shutdown()
        processor.shutdown()

        # Verify exporter shutdown was called multiple times (this is expected behavior)
        assert mock_exporter.shutdown.call_count == 3

    @patch("agentops.sdk.processors.logger")
    def test_shutdown_timeout_behavior(self, mock_logger):
        """Test the specific timeout behavior during shutdown."""
        # Create a mock exporter
        mock_exporter = MagicMock()

        # Create processor
        processor = LiveSpanProcessor(mock_exporter)

        # Track the actual timeout used
        original_join = processor._export_thread.join
        join_timeout = None

        def capture_join_timeout(timeout=None):
            nonlocal join_timeout
            join_timeout = timeout
            # Simulate thread not terminating within timeout
            if timeout is not None:
                time.sleep(0.01)  # Small delay to simulate timeout
            return original_join(timeout=0.01)  # Quick join to actually stop thread

        with patch.object(processor._export_thread, "join", side_effect=capture_join_timeout):
            with patch.object(processor._export_thread, "is_alive", return_value=True):
                # Shutdown
                processor.shutdown()

                # Verify the timeout was 5.0 seconds
                assert join_timeout == 5.0

                # Verify warning was logged
                mock_logger.warning.assert_called_once_with(
                    "Export thread did not shut down within timeout, continuing shutdown"
                )


class TestLiveSpanProcessorThreadSafety:
    """Tests for thread safety during LiveSpanProcessor operations."""

    def test_concurrent_shutdown_calls(self):
        """Test that concurrent shutdown calls are handled safely."""
        # Create a mock exporter
        mock_exporter = MagicMock()

        # Create processor
        processor = LiveSpanProcessor(mock_exporter)

        # Create multiple threads that call shutdown
        shutdown_threads = []
        exceptions = []

        def shutdown_worker():
            try:
                processor.shutdown()
            except Exception as e:
                exceptions.append(e)

        # Start multiple shutdown threads
        for _ in range(5):
            thread = threading.Thread(target=shutdown_worker)
            shutdown_threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in shutdown_threads:
            thread.join()

        # Verify no exceptions occurred
        assert len(exceptions) == 0

        # Verify exporter shutdown was called (multiple times is expected)
        assert mock_exporter.shutdown.call_count >= 1

    def test_shutdown_during_span_processing(self):
        """Test shutdown while spans are being processed."""
        # Create a mock exporter that takes time to export
        mock_exporter = MagicMock()

        def slow_export(spans):
            time.sleep(0.1)  # Simulate slow export
            return True

        mock_exporter.export.side_effect = slow_export

        # Create processor
        processor = LiveSpanProcessor(mock_exporter)

        # Create a mock span with proper context
        mock_span = MagicMock()
        mock_span.context.span_id = 12345
        mock_span.context.trace_flags.sampled = True

        # Properly initialize the span through on_start (realistic lifecycle)
        processor.on_start(mock_span, None)

        # Start processing a span in a separate thread
        def process_span():
            processor.on_end(mock_span)

        process_thread = threading.Thread(target=process_span)
        process_thread.start()

        # Give the processing thread a moment to start
        time.sleep(0.05)

        # Shutdown while processing
        processor.shutdown()

        # Wait for processing thread to complete
        process_thread.join(timeout=1.0)

        # Verify shutdown completed successfully
        assert not processor._export_thread.is_alive()


class TestLiveSpanProcessorResourceManagement:
    """Tests for proper resource management in LiveSpanProcessor."""

    def test_stop_event_set_during_shutdown(self):
        """Test that stop event is properly set during shutdown."""
        # Create a mock exporter
        mock_exporter = MagicMock()

        # Create processor
        processor = LiveSpanProcessor(mock_exporter)

        # Verify stop event is not set initially
        assert not processor._stop_event.is_set()

        # Shutdown
        processor.shutdown()

        # Verify stop event is set
        assert processor._stop_event.is_set()

    def test_export_thread_lifecycle(self):
        """Test the complete lifecycle of the export thread."""
        # Create a mock exporter
        mock_exporter = MagicMock()

        # Create processor
        processor = LiveSpanProcessor(mock_exporter)

        # Verify thread is created and running
        assert processor._export_thread is not None
        assert processor._export_thread.is_alive()
        assert processor._export_thread.daemon  # Should be daemon thread

        # Shutdown
        processor.shutdown()

        # Verify thread is stopped
        assert not processor._export_thread.is_alive()

    @patch("agentops.sdk.processors.logger")
    def test_graceful_degradation_on_errors(self, mock_logger):
        """Test that processor gracefully degrades when errors occur during shutdown."""
        # Create a mock exporter
        mock_exporter = MagicMock()

        # Create processor
        processor = LiveSpanProcessor(mock_exporter)

        # Mock everything to fail
        with patch.object(processor._stop_event, "set", side_effect=Exception("Stop event failed")):
            with patch.object(processor._export_thread, "join", side_effect=Exception("Join failed")):
                with patch.object(processor._export_thread, "is_alive", side_effect=Exception("is_alive failed")):
                    mock_exporter.shutdown.side_effect = Exception("Exporter shutdown failed")

                    # Shutdown should still complete without raising exceptions
                    processor.shutdown()

                    # Verify errors were logged but execution continued
                    assert mock_logger.error.call_count >= 1


class TestLiveSpanProcessorBackwardCompatibility:
    """Tests to ensure backward compatibility of LiveSpanProcessor."""

    def test_force_flush_unchanged(self):
        """Test that force_flush behavior is unchanged."""
        # Create a mock exporter
        mock_exporter = MagicMock()

        # Create processor
        processor = LiveSpanProcessor(mock_exporter)

        # Test force_flush
        result = processor.force_flush()

        # Should return True (unchanged behavior)
        assert result is True

    def test_on_start_unchanged(self):
        """Test that on_start behavior is unchanged."""
        # Create a mock exporter
        mock_exporter = MagicMock()

        # Create processor
        processor = LiveSpanProcessor(mock_exporter)

        # Create a mock span
        mock_span = MagicMock()

        # Test on_start (should not raise exception)
        processor.on_start(mock_span, None)

    def test_on_end_unchanged(self):
        """Test that on_end behavior is unchanged."""
        # Create a mock exporter
        mock_exporter = MagicMock()

        # Create processor
        processor = LiveSpanProcessor(mock_exporter)

        # Create a mock span with proper context
        mock_span = MagicMock()
        mock_span.context.span_id = 12345
        mock_span.context.trace_flags.sampled = True

        # Add the span to _in_flight first (simulating on_start)
        processor._in_flight[mock_span.context.span_id] = mock_span

        # Test on_end
        processor.on_end(mock_span)

        # Verify exporter.export was called
        mock_exporter.export.assert_called_once_with((mock_span,))

        # Verify span was removed from _in_flight
        assert mock_span.context.span_id not in processor._in_flight
