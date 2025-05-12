"""
Unit tests for dashboard URL generation and logging.
"""

import unittest
from unittest.mock import patch, MagicMock

from agentops.helpers.dashboard import get_trace_url, log_trace_url


class TestDashboardHelpers(unittest.TestCase):
    """Tests for dashboard URL generation and logging functions."""

    @patch("agentops.get_client")
    def test_get_trace_url_with_hex_trace_id(self, mock_get_client):
        """Test get_trace_url with a hexadecimal trace ID."""
        # Mock the config's app_url
        mock_client = MagicMock()
        mock_client.config.app_url = "https://test-app.agentops.ai"
        mock_get_client.return_value = mock_client

        # Create a mock span with a hex string trace ID (using a full 32-character trace ID)
        mock_span = MagicMock()
        mock_span.context.trace_id = "1234567890abcdef1234567890abcdef"

        # Call get_trace_url
        url = get_trace_url(mock_span)

        # Assert that the URL is correctly formed with the config's app_url
        self.assertEqual(url, "https://test-app.agentops.ai/sessions?trace_id=1234567890abcdef1234567890abcdef")

    @patch("agentops.get_client")
    def test_get_trace_url_with_int_trace_id(self, mock_get_client):
        """Test get_trace_url with an integer trace ID."""
        # Mock the config's app_url
        mock_client = MagicMock()
        mock_client.config.app_url = "https://test-app.agentops.ai"
        mock_get_client.return_value = mock_client

        # Create a mock span with an int trace ID
        mock_span = MagicMock()
        mock_span.context.trace_id = 12345

        # Call get_trace_url
        url = get_trace_url(mock_span)

        # Assert that the URL follows the expected format with a 32-character hex string
        self.assertTrue(url.startswith("https://test-app.agentops.ai/sessions?trace_id="))

        # Verify the format is a 32-character hex string (no dashes)
        hex_part = url.split("trace_id=")[1]
        self.assertRegex(hex_part, r"^[0-9a-f]{32}$")

        # Verify the value is correctly formatted from the integer 12345
        expected_hex = format(12345, "032x")
        self.assertEqual(hex_part, expected_hex)

    @patch("agentops.helpers.dashboard.logger")
    @patch("agentops.get_client")
    def test_log_trace_url(self, mock_get_client, mock_logger):
        """Test log_trace_url includes the session URL in the log message."""
        # Mock the config's app_url
        mock_client = MagicMock()
        mock_client.config.app_url = "https://test-app.agentops.ai"
        mock_get_client.return_value = mock_client

        # Create a mock span
        mock_span = MagicMock()
        mock_span.context.trace_id = "test-trace-id"

        # Mock get_trace_url to return a known value that uses the app_url
        expected_url = "https://test-app.agentops.ai/sessions?trace_id=test-trace-id"
        with patch("agentops.helpers.dashboard.get_trace_url", return_value=expected_url):
            # Call log_trace_url
            log_trace_url(mock_span)

            # Assert that logger.info was called with a message containing the URL
            mock_logger.info.assert_called_once()
            log_message = mock_logger.info.call_args[0][0]
            self.assertIn(expected_url, log_message)
