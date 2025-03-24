"""
Unit tests for dashboard URL generation and logging.
"""

import unittest
from unittest.mock import patch, MagicMock

from agentops.helpers.dashboard import get_trace_url, log_trace_url


class TestDashboardHelpers(unittest.TestCase):
    """Tests for dashboard URL generation and logging functions."""

    def test_get_trace_url_with_hex_trace_id(self):
        """Test get_trace_url with a hexadecimal trace ID."""
        # Create a mock span with a hex string trace ID
        mock_span = MagicMock()
        mock_span.context.trace_id = "1234567890abcdef"
        
        # Call get_trace_url
        url = get_trace_url(mock_span)
        
        # Assert that the URL is correctly formed
        self.assertEqual(url, "https://app.agentops.ai/sessions?trace_id=1234567890abcdef")

    def test_get_trace_url_with_int_trace_id(self):
        """Test get_trace_url with an integer trace ID."""
        # Create a mock span with an int trace ID
        mock_span = MagicMock()
        mock_span.context.trace_id = 12345
        
        # Call get_trace_url
        url = get_trace_url(mock_span)
        
        # Assert that the URL follows the expected format with a UUID
        self.assertTrue(url.startswith("https://app.agentops.ai/sessions?trace_id="))
        # Verify the format matches UUID pattern (8-4-4-4-12 hex digits)
        uuid_part = url.split("trace_id=")[1]
        self.assertRegex(uuid_part, r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

    @patch('agentops.helpers.dashboard.logger')
    def test_log_trace_url(self, mock_logger):
        """Test log_trace_url includes the session URL in the log message."""
        # Create a mock span
        mock_span = MagicMock()
        mock_span.context.trace_id = "test-trace-id"
        
        # Mock get_trace_url to return a known value
        expected_url = "https://app.agentops.ai/sessions?trace_id=test-trace-id"
        with patch('agentops.helpers.dashboard.get_trace_url', return_value=expected_url):
            # Call log_trace_url
            log_trace_url(mock_span)
            
            # Assert that logger.info was called with a message containing the URL
            mock_logger.info.assert_called_once()
            log_message = mock_logger.info.call_args[0][0]
            self.assertIn(expected_url, log_message)