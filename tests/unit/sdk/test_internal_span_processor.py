"""
Unit tests for URL logging functionality and InternalSpanProcessor.
"""

import unittest
from unittest.mock import patch, MagicMock

from opentelemetry.sdk.trace import Span, ReadableSpan

from agentops.sdk.processors import InternalSpanProcessor
from agentops.sdk.core import TraceContext, tracer


class TestURLLogging(unittest.TestCase):
    """Tests for URL logging functionality in global tracer."""

    def setUp(self):
        self.tracing_core = tracer
        # Mock the initialization to avoid actual setup
        self.tracing_core._initialized = True
        self.tracing_core._config = {"project_id": "test_project"}

    @patch("agentops.sdk.core.log_trace_url")
    @patch("agentops.sdk.core.tracer.make_span")
    def test_start_trace_logs_url(self, mock_make_span, mock_log_trace_url):
        """Test that start_trace logs the trace URL."""
        # Create a mock span
        mock_span = MagicMock(spec=Span)
        mock_context = MagicMock()
        mock_token = MagicMock()
        mock_span.get_span_context.return_value.span_id = 12345
        mock_make_span.return_value = (mock_span, mock_context, mock_token)

        # Call start_trace
        trace_context = self.tracing_core.start_trace(trace_name="test_trace")

        # Assert that log_trace_url was called with the span and title
        mock_log_trace_url.assert_called_once_with(mock_span, title="test_trace")
        self.assertIsInstance(trace_context, TraceContext)
        self.assertEqual(trace_context.span, mock_span)

    @patch("agentops.sdk.core.log_trace_url")
    @patch("agentops.sdk.core.tracer.finalize_span")
    def test_end_trace_logs_url(self, mock_finalize_span, mock_log_trace_url):
        """Test that end_trace logs the trace URL."""
        # Create a mock trace context
        mock_span = MagicMock(spec=Span)
        mock_span.name = "test_trace"
        mock_span.get_span_context.return_value.span_id = 12345
        mock_token = MagicMock()
        trace_context = TraceContext(mock_span, mock_token)

        # Call end_trace
        self.tracing_core.end_trace(trace_context, "Success")

        # Assert that log_trace_url was called with the span and title
        mock_log_trace_url.assert_called_once_with(mock_span, title="test_trace")

    @patch("agentops.sdk.core.log_trace_url")
    @patch("agentops.sdk.core.tracer.make_span")
    def test_start_trace_url_logging_failure_does_not_break_trace(self, mock_make_span, mock_log_trace_url):
        """Test that URL logging failure doesn't break trace creation."""
        # Create a mock span
        mock_span = MagicMock(spec=Span)
        mock_context = MagicMock()
        mock_token = MagicMock()
        mock_span.get_span_context.return_value.span_id = 12345
        mock_make_span.return_value = (mock_span, mock_context, mock_token)

        # Make log_trace_url raise an exception
        mock_log_trace_url.side_effect = Exception("URL logging failed")

        # Call start_trace - should not raise exception
        trace_context = self.tracing_core.start_trace(trace_name="test_trace")

        # Assert that trace was still created successfully
        self.assertIsInstance(trace_context, TraceContext)
        self.assertEqual(trace_context.span, mock_span)
        mock_log_trace_url.assert_called_once_with(mock_span, title="test_trace")

    @patch("agentops.sdk.core.log_trace_url")
    @patch("agentops.sdk.core.tracer.finalize_span")
    def test_end_trace_url_logging_failure_does_not_break_trace(self, mock_finalize_span, mock_log_trace_url):
        """Test that URL logging failure doesn't break trace ending."""
        # Create a mock trace context
        mock_span = MagicMock(spec=Span)
        mock_span.name = "test_trace"
        mock_span.get_span_context.return_value.span_id = 12345
        mock_token = MagicMock()
        trace_context = TraceContext(mock_span, mock_token)

        # Make log_trace_url raise an exception
        mock_log_trace_url.side_effect = Exception("URL logging failed")

        # Call end_trace - should not raise exception
        self.tracing_core.end_trace(trace_context, "Success")

        # Assert that finalize_span was still called
        mock_finalize_span.assert_called_once()
        mock_log_trace_url.assert_called_once_with(mock_span, title="test_trace")

    @patch("agentops.sdk.core.log_trace_url")
    @patch("agentops.sdk.core.tracer.make_span")
    def test_start_trace_with_tags_logs_url(self, mock_make_span, mock_log_trace_url):
        """Test that start_trace with tags logs the trace URL."""
        # Create a mock span
        mock_span = MagicMock(spec=Span)
        mock_context = MagicMock()
        mock_token = MagicMock()
        mock_span.get_span_context.return_value.span_id = 12345
        mock_make_span.return_value = (mock_span, mock_context, mock_token)

        # Call start_trace with tags
        trace_context = self.tracing_core.start_trace(trace_name="tagged_trace", tags=["test", "integration"])

        # Assert that log_trace_url was called with the span and title
        mock_log_trace_url.assert_called_once_with(mock_span, title="tagged_trace")
        self.assertIsInstance(trace_context, TraceContext)


class TestSessionDecoratorURLLogging(unittest.TestCase):
    """Tests for URL logging functionality in session decorators."""

    def setUp(self):
        self.tracing_core = tracer
        # Mock the initialization to avoid actual setup
        self.tracing_core._initialized = True
        self.tracing_core._config = {"project_id": "test_project"}

    @patch("agentops.sdk.core.log_trace_url")
    @patch("agentops.sdk.core.tracer.make_span")
    @patch("agentops.sdk.core.tracer.finalize_span")
    def test_session_decorator_logs_url_on_start_and_end(self, mock_finalize_span, mock_make_span, mock_log_trace_url):
        """Test that session decorator logs URLs on both start and end."""
        from agentops.sdk.decorators import session

        # Create a mock span
        mock_span = MagicMock(spec=Span)
        mock_span.name = "test_function"
        mock_context = MagicMock()
        mock_token = MagicMock()
        mock_span.get_span_context.return_value.span_id = 12345
        mock_make_span.return_value = (mock_span, mock_context, mock_token)

        @session(name="test_session")
        def test_function():
            return "test_result"

        # Call the decorated function
        result = test_function()

        # Assert that log_trace_url was called (start and end)
        # Note: The actual number of calls may vary based on implementation details
        self.assertGreaterEqual(mock_log_trace_url.call_count, 2)
        # Verify that the calls include the expected session name
        call_args_list = [
            call_args[1]["title"] for call_args in mock_log_trace_url.call_args_list if "title" in call_args[1]
        ]
        self.assertIn("test_session", call_args_list)
        self.assertEqual(result, "test_result")

    @patch("agentops.sdk.core.log_trace_url")
    @patch("agentops.sdk.core.tracer.make_span")
    @patch("agentops.sdk.core.tracer.finalize_span")
    def test_session_decorator_with_default_name_logs_url(self, mock_finalize_span, mock_make_span, mock_log_trace_url):
        """Test that session decorator with default name logs URLs."""
        from agentops.sdk.decorators import session

        # Create a mock span
        mock_span = MagicMock(spec=Span)
        mock_span.name = "my_function"
        mock_context = MagicMock()
        mock_token = MagicMock()
        mock_span.get_span_context.return_value.span_id = 12345
        mock_make_span.return_value = (mock_span, mock_context, mock_token)

        @session
        def my_function():
            return "result"

        # Call the decorated function
        result = my_function()

        # Assert that log_trace_url was called with function name as title
        self.assertGreaterEqual(mock_log_trace_url.call_count, 2)
        # Verify that the calls include the expected function name
        call_args_list = [
            call_args[1]["title"] for call_args in mock_log_trace_url.call_args_list if "title" in call_args[1]
        ]
        self.assertIn("my_function", call_args_list)
        self.assertEqual(result, "result")

    @patch("agentops.sdk.core.log_trace_url")
    @patch("agentops.sdk.core.tracer.make_span")
    @patch("agentops.sdk.core.tracer.finalize_span")
    def test_session_decorator_handles_url_logging_failure(
        self, mock_finalize_span, mock_make_span, mock_log_trace_url
    ):
        """Test that session decorator handles URL logging failures gracefully."""
        from agentops.sdk.decorators import session

        # Create a mock span
        mock_span = MagicMock(spec=Span)
        mock_span.name = "test_function"
        mock_context = MagicMock()
        mock_token = MagicMock()
        mock_span.get_span_context.return_value.span_id = 12345
        mock_make_span.return_value = (mock_span, mock_context, mock_token)

        # Make log_trace_url raise an exception
        mock_log_trace_url.side_effect = Exception("URL logging failed")

        @session(name="failing_session")
        def test_function():
            return "test_result"

        # Call the decorated function - should not raise exception
        result = test_function()

        # Assert that function still executed successfully
        self.assertEqual(result, "test_result")
        # Assert that log_trace_url was called (even though it failed)
        self.assertGreaterEqual(mock_log_trace_url.call_count, 2)


class TestInternalSpanProcessor(unittest.TestCase):
    """Tests for InternalSpanProcessor functionality."""

    def setUp(self):
        self.processor = InternalSpanProcessor()
        # Reset the root span ID before each test
        self.processor._root_span_id = None

    def test_tracks_root_span_on_start(self):
        """Test that the processor tracks the first span as root span."""
        # Create a mock span
        mock_span = MagicMock(spec=Span)
        mock_context = MagicMock()
        mock_context.trace_flags.sampled = True
        mock_context.span_id = 12345
        mock_span.context = mock_context

        # Call on_start
        self.processor.on_start(mock_span)

        # Assert that root span ID was set
        self.assertEqual(self.processor._root_span_id, 12345)

    def test_ignores_unsampled_spans_on_start(self):
        """Test that unsampled spans are ignored on start."""
        # Create a mock unsampled span
        mock_span = MagicMock(spec=Span)
        mock_context = MagicMock()
        mock_context.trace_flags.sampled = False
        mock_span.context = mock_context

        # Call on_start
        self.processor.on_start(mock_span)

        # Assert that root span ID was not set
        self.assertIsNone(self.processor._root_span_id)

    def test_only_tracks_first_span_as_root(self):
        """Test that only the first span is tracked as root span."""
        # First span
        mock_span1 = MagicMock(spec=Span)
        mock_context1 = MagicMock()
        mock_context1.trace_flags.sampled = True
        mock_context1.span_id = 12345
        mock_span1.context = mock_context1

        # Second span
        mock_span2 = MagicMock(spec=Span)
        mock_context2 = MagicMock()
        mock_context2.trace_flags.sampled = True
        mock_context2.span_id = 67890
        mock_span2.context = mock_context2

        # Start first span
        self.processor.on_start(mock_span1)
        self.assertEqual(self.processor._root_span_id, 12345)

        # Start second span - should not change root span ID
        self.processor.on_start(mock_span2)
        self.assertEqual(self.processor._root_span_id, 12345)

    @patch("agentops.sdk.processors.upload_logfile")
    def test_uploads_logfile_on_root_span_end(self, mock_upload_logfile):
        """Test that logfile is uploaded when root span ends."""
        # Set up root span
        mock_span = MagicMock(spec=Span)
        mock_context = MagicMock()
        mock_context.trace_flags.sampled = True
        mock_context.span_id = 12345
        mock_context.trace_id = 98765
        mock_span.context = mock_context

        # Start the span to set it as root
        self.processor.on_start(mock_span)

        # Create readable span for end event
        mock_readable_span = MagicMock(spec=ReadableSpan)
        mock_readable_span.context = mock_context

        # End the span
        self.processor.on_end(mock_readable_span)

        # Assert that upload_logfile was called with trace_id
        mock_upload_logfile.assert_called_once_with(98765)

    @patch("agentops.sdk.processors.upload_logfile")
    def test_does_not_upload_logfile_for_non_root_span(self, mock_upload_logfile):
        """Test that logfile is not uploaded for non-root spans."""
        # Set up root span
        root_span = MagicMock(spec=Span)
        root_context = MagicMock()
        root_context.trace_flags.sampled = True
        root_context.span_id = 12345
        root_span.context = root_context

        # Start root span
        self.processor.on_start(root_span)

        # Create non-root span
        non_root_span = MagicMock(spec=ReadableSpan)
        non_root_context = MagicMock()
        non_root_context.trace_flags.sampled = True
        non_root_context.span_id = 67890  # Different from root
        non_root_span.context = non_root_context

        # End non-root span
        self.processor.on_end(non_root_span)

        # Assert that upload_logfile was not called
        mock_upload_logfile.assert_not_called()

    @patch("agentops.sdk.processors.upload_logfile")
    def test_handles_upload_logfile_error(self, mock_upload_logfile):
        """Test that processor handles upload_logfile errors gracefully."""
        # Set up root span
        mock_span = MagicMock(spec=Span)
        mock_context = MagicMock()
        mock_context.trace_flags.sampled = True
        mock_context.span_id = 12345
        mock_context.trace_id = 98765
        mock_span.context = mock_context

        # Start the span to set it as root
        self.processor.on_start(mock_span)

        # Make upload_logfile raise an exception
        mock_upload_logfile.side_effect = Exception("Upload failed")

        # Create readable span for end event
        mock_readable_span = MagicMock(spec=ReadableSpan)
        mock_readable_span.context = mock_context

        # End the span - should not raise exception
        self.processor.on_end(mock_readable_span)

        # Assert that upload_logfile was called
        mock_upload_logfile.assert_called_once_with(98765)

    def test_ignores_unsampled_spans_on_end(self):
        """Test that unsampled spans are ignored on end."""
        # Create a mock unsampled span
        mock_span = MagicMock(spec=ReadableSpan)
        mock_context = MagicMock()
        mock_context.trace_flags.sampled = False
        mock_span.context = mock_context

        # Call on_end - should not raise exception
        self.processor.on_end(mock_span)

    def test_shutdown_resets_root_span_id(self):
        """Test that shutdown resets the root span ID."""
        # Set up root span
        mock_span = MagicMock(spec=Span)
        mock_context = MagicMock()
        mock_context.trace_flags.sampled = True
        mock_context.span_id = 12345
        mock_span.context = mock_context

        # Start span to set root span ID
        self.processor.on_start(mock_span)
        self.assertEqual(self.processor._root_span_id, 12345)

        # Call shutdown
        self.processor.shutdown()

        # Verify root span ID was reset
        self.assertIsNone(self.processor._root_span_id)

    def test_force_flush_returns_true(self):
        """Test that force_flush returns True."""
        result = self.processor.force_flush()
        self.assertTrue(result)
