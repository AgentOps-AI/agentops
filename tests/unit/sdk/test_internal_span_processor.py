"""
Unit tests for the InternalSpanProcessor.
"""

import unittest
from unittest.mock import patch, MagicMock, call

from opentelemetry.sdk.trace import Span, ReadableSpan

from agentops.sdk.processors import InternalSpanProcessor


class TestInternalSpanProcessor(unittest.TestCase):
    """Tests for InternalSpanProcessor."""

    def setUp(self):
        self.processor = InternalSpanProcessor()
        
        # Reset the root span ID before each test
        self.processor._root_span_id = None

    @patch('agentops.sdk.processors.log_trace_url')
    def test_logs_url_for_first_span(self, mock_log_trace_url):
        """Test that the first span triggers a log_trace_url call."""
        # Create a mock span
        mock_span = MagicMock(spec=Span)
        mock_context = MagicMock()
        mock_context.trace_flags.sampled = True
        mock_context.span_id = 12345
        mock_span.context = mock_context
        
        # Call on_start
        self.processor.on_start(mock_span)
        
        # Assert that log_trace_url was called once
        mock_log_trace_url.assert_called_once_with(mock_span)

    @patch('agentops.sdk.processors.log_trace_url')
    def test_logs_url_only_for_root_span(self, mock_log_trace_url):
        """Test that log_trace_url is only called for the root span."""
        # First, create and start the root span
        mock_root_span = MagicMock(spec=Span)
        mock_root_context = MagicMock()
        mock_root_context.trace_flags.sampled = True
        mock_root_context.span_id = 12345
        mock_root_span.context = mock_root_context
        
        self.processor.on_start(mock_root_span)
        
        # Reset the mock after root span creation
        mock_log_trace_url.reset_mock()
        
        # Now create and start a non-root span
        mock_non_root_span = MagicMock(spec=Span)
        mock_non_root_context = MagicMock()
        mock_non_root_context.trace_flags.sampled = True
        mock_non_root_context.span_id = 67890  # Different from root span ID
        mock_non_root_span.context = mock_non_root_context
        
        self.processor.on_start(mock_non_root_span)
        
        # Assert that log_trace_url was not called for the non-root span
        mock_log_trace_url.assert_not_called()
        
        # End the non-root span
        mock_non_root_readable = MagicMock(spec=ReadableSpan)
        mock_non_root_readable.context = mock_non_root_context
        
        self.processor.on_end(mock_non_root_readable)
        
        # Assert that log_trace_url was still not called
        mock_log_trace_url.assert_not_called()
        
        # Now end the root span
        mock_root_readable = MagicMock(spec=ReadableSpan)
        mock_root_readable.context = mock_root_context
        
        self.processor.on_end(mock_root_readable)
        
        # Assert that log_trace_url was called for the root span end
        mock_log_trace_url.assert_called_once_with(mock_root_readable)

    @patch('agentops.sdk.processors.log_trace_url')
    def test_logs_url_exactly_twice_for_root_span(self, mock_log_trace_url):
        """Test that log_trace_url is called exactly twice for the root span (start and end)."""
        # Create a mock root span
        mock_root_span = MagicMock(spec=Span)
        mock_root_context = MagicMock()
        mock_root_context.trace_flags.sampled = True
        mock_root_context.span_id = 12345
        mock_root_span.context = mock_root_context
        
        # Start the root span
        self.processor.on_start(mock_root_span)
        
        # Create a mock readable span for the end event
        mock_root_readable = MagicMock(spec=ReadableSpan)
        mock_root_readable.context = mock_root_context
        
        # End the root span
        self.processor.on_end(mock_root_readable)
        
        # Assert that log_trace_url was called exactly twice
        self.assertEqual(mock_log_trace_url.call_count, 2)
        mock_log_trace_url.assert_has_calls([
            call(mock_root_span),
            call(mock_root_readable)
        ])

    @patch('agentops.sdk.processors.log_trace_url')
    def test_ignores_unsampled_spans(self, mock_log_trace_url):
        """Test that unsampled spans are ignored."""
        # Create a mock unsampled span
        mock_span = MagicMock(spec=Span)
        mock_context = MagicMock()
        mock_context.trace_flags.sampled = False
        mock_span.context = mock_context
        
        # Start and end the span
        self.processor.on_start(mock_span)
        self.processor.on_end(mock_span)
        
        # Assert that log_trace_url was not called
        mock_log_trace_url.assert_not_called()
        
        # Assert that root_span_id was not set
        self.assertIsNone(self.processor._root_span_id)

    @patch('agentops.sdk.processors.log_trace_url')
    def test_shutdown_resets_root_span_id(self, mock_log_trace_url):
        """Test that shutdown resets the root span ID."""
        # First set a root span
        mock_root_span = MagicMock(spec=Span)
        mock_root_context = MagicMock()
        mock_root_context.trace_flags.sampled = True
        mock_root_context.span_id = 12345
        mock_root_span.context = mock_root_context
        
        self.processor.on_start(mock_root_span)
        
        # Verify root span ID was set
        self.assertEqual(self.processor._root_span_id, 12345)
        
        # Call shutdown
        self.processor.shutdown()
        
        # Verify root span ID was reset
        self.assertIsNone(self.processor._root_span_id)
        
        # Create another span after shutdown
        mock_span = MagicMock(spec=Span)
        mock_context = MagicMock()
        mock_context.trace_flags.sampled = True
        mock_context.span_id = 67890
        mock_span.context = mock_context
        
        # Reset mocks
        mock_log_trace_url.reset_mock()
        
        # Start the span, it should be treated as a new root span
        self.processor.on_start(mock_span)
        
        # Verify new root span was identified
        self.assertEqual(self.processor._root_span_id, 67890)
        mock_log_trace_url.assert_called_once_with(mock_span)