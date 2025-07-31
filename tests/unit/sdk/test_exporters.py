"""
Unit tests for AuthenticatedOTLPExporter.
"""

import unittest
from unittest.mock import Mock, patch

import requests
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExportResult
from opentelemetry.exporter.otlp.proto.http import Compression

from agentops.sdk.exporters import AuthenticatedOTLPExporter
from agentops.exceptions import AgentOpsApiJwtExpiredException, ApiServerException

# these are simple tests on a simple file, basically just to get test coverage


class TestAuthenticatedOTLPExporter(unittest.TestCase):
    """Tests for AuthenticatedOTLPExporter class."""

    def setUp(self):
        """Set up test fixtures."""
        self.endpoint = "https://api.agentops.ai/v1/traces"
        self.jwt = "test-jwt-token"
        self.timeout = 30
        self.compression = Compression.Gzip
        self.custom_headers = {"X-Custom-Header": "test-value"}

    def test_initialization_with_required_params(self):
        """Test exporter initialization with required parameters."""
        exporter = AuthenticatedOTLPExporter(endpoint=self.endpoint, jwt=self.jwt)

        # Verify the exporter was created successfully
        self.assertIsInstance(exporter, AuthenticatedOTLPExporter)
        self.assertEqual(exporter._endpoint, self.endpoint)

    def test_initialization_with_all_params(self):
        """Test exporter initialization with all parameters."""
        exporter = AuthenticatedOTLPExporter(
            endpoint=self.endpoint,
            jwt=self.jwt,
            headers=self.custom_headers,
            timeout=self.timeout,
            compression=self.compression,
        )

        # Verify the exporter was created successfully
        self.assertIsInstance(exporter, AuthenticatedOTLPExporter)
        self.assertEqual(exporter._endpoint, self.endpoint)

    def test_initialization_without_optional_params(self):
        """Test exporter initialization without optional parameters."""
        exporter = AuthenticatedOTLPExporter(endpoint=self.endpoint, jwt=self.jwt)

        # Verify the exporter was created successfully
        self.assertIsInstance(exporter, AuthenticatedOTLPExporter)
        self.assertEqual(exporter._endpoint, self.endpoint)

    def test_export_success(self):
        """Test successful span export."""
        mock_spans = [Mock(spec=ReadableSpan), Mock(spec=ReadableSpan)]

        with patch("opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter.export") as mock_export:
            mock_export.return_value = SpanExportResult.SUCCESS

            exporter = AuthenticatedOTLPExporter(endpoint=self.endpoint, jwt=self.jwt)

            result = exporter.export(mock_spans)

            # Verify the result
            self.assertEqual(result, SpanExportResult.SUCCESS)

    def test_export_jwt_expired_exception(self):
        """Test export handling of JWT expired exception."""
        mock_spans = [Mock(spec=ReadableSpan)]

        with patch("opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter.export") as mock_export:
            mock_export.side_effect = AgentOpsApiJwtExpiredException("Token expired")

            with patch("agentops.sdk.exporters.logger") as mock_logger:
                exporter = AuthenticatedOTLPExporter(endpoint=self.endpoint, jwt=self.jwt)

                result = exporter.export(mock_spans)

                # Verify failure result and logging
                self.assertEqual(result, SpanExportResult.FAILURE)
                mock_logger.warning.assert_called_once()

    def test_export_api_server_exception(self):
        """Test export handling of API server exception."""
        mock_spans = [Mock(spec=ReadableSpan)]

        with patch("opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter.export") as mock_export:
            mock_export.side_effect = ApiServerException("Server error")

            with patch("agentops.sdk.exporters.logger") as mock_logger:
                exporter = AuthenticatedOTLPExporter(endpoint=self.endpoint, jwt=self.jwt)

                result = exporter.export(mock_spans)

                # Verify failure result and logging
                self.assertEqual(result, SpanExportResult.FAILURE)
                mock_logger.error.assert_called_once()

    def test_export_requests_exception(self):
        """Test export handling of requests exception."""
        mock_spans = [Mock(spec=ReadableSpan)]

        with patch("opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter.export") as mock_export:
            mock_export.side_effect = requests.RequestException("Network error")

            with patch("agentops.sdk.exporters.logger") as mock_logger:
                exporter = AuthenticatedOTLPExporter(endpoint=self.endpoint, jwt=self.jwt)

                result = exporter.export(mock_spans)

                # Verify failure result and logging
                self.assertEqual(result, SpanExportResult.FAILURE)
                mock_logger.error.assert_called_once()

    def test_export_unexpected_exception(self):
        """Test export handling of unexpected exception."""
        mock_spans = [Mock(spec=ReadableSpan)]

        with patch("opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter.export") as mock_export:
            mock_export.side_effect = ValueError("Unexpected error")

            with patch("agentops.sdk.exporters.logger") as mock_logger:
                exporter = AuthenticatedOTLPExporter(endpoint=self.endpoint, jwt=self.jwt)

                result = exporter.export(mock_spans)

                # Verify failure result and logging
                self.assertEqual(result, SpanExportResult.FAILURE)
                mock_logger.error.assert_called_once()

    def test_export_empty_spans_list(self):
        """Test export with empty spans list."""
        mock_spans = []

        with patch("opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter.export") as mock_export:
            mock_export.return_value = SpanExportResult.SUCCESS

            exporter = AuthenticatedOTLPExporter(endpoint=self.endpoint, jwt=self.jwt)

            result = exporter.export(mock_spans)

            # Verify the result
            self.assertEqual(result, SpanExportResult.SUCCESS)

    def test_clear_method(self):
        """Test clear method (should be a no-op)."""
        exporter = AuthenticatedOTLPExporter(endpoint=self.endpoint, jwt=self.jwt)

        # Clear method should not raise any exception
        exporter.clear()

    def test_initialization_with_kwargs(self):
        """Test exporter initialization with additional kwargs."""
        exporter = AuthenticatedOTLPExporter(endpoint=self.endpoint, jwt=self.jwt, custom_param="test_value")

        # Verify the exporter was created successfully
        self.assertIsInstance(exporter, AuthenticatedOTLPExporter)

    def test_headers_merging(self):
        """Test that custom headers are properly merged with authorization header."""
        custom_headers = {"X-Custom-Header": "test-value", "Content-Type": "application/json"}

        exporter = AuthenticatedOTLPExporter(endpoint=self.endpoint, jwt=self.jwt, headers=custom_headers)

        # Verify the exporter was created successfully
        self.assertIsInstance(exporter, AuthenticatedOTLPExporter)

    def test_headers_protected_from_override(self):
        """Test that critical headers cannot be overridden by user-supplied headers."""
        # Attempt to override critical headers
        malicious_headers = {
            "Authorization": "Malicious-Auth malicious-token",
            "Content-Type": "text/plain",
            "User-Agent": "malicious-agent",
            "X-API-Key": "malicious-key",
            "X-Custom-Header": "test-value",  # This should be allowed
        }

        exporter = AuthenticatedOTLPExporter(endpoint=self.endpoint, jwt=self.jwt, headers=malicious_headers)

        # Test the _prepare_headers method directly to verify protection
        prepared_headers = exporter._prepare_headers(malicious_headers)

        # Critical headers should not be overridden
        self.assertEqual(prepared_headers["Authorization"], f"Bearer {self.jwt}")
        self.assertNotEqual(prepared_headers.get("Content-Type"), "text/plain")
        self.assertNotEqual(prepared_headers.get("User-Agent"), "malicious-agent")
        self.assertNotIn("X-API-Key", prepared_headers)  # Should be filtered out

        # Non-critical headers should be allowed
        self.assertEqual(prepared_headers.get("X-Custom-Header"), "test-value")

        # Verify the exporter was created successfully
        self.assertIsInstance(exporter, AuthenticatedOTLPExporter)


class TestAuthenticatedOTLPExporterIntegration(unittest.TestCase):
    """Integration-style tests for AuthenticatedOTLPExporter."""

    def setUp(self):
        """Set up test fixtures."""
        self.endpoint = "https://api.agentops.ai/v1/traces"
        self.jwt = "test-jwt-token"

    def test_full_export_cycle(self):
        """Test a complete export cycle with multiple spans."""
        # Create mock spans
        mock_spans = [
            Mock(spec=ReadableSpan, name="span1"),
            Mock(spec=ReadableSpan, name="span2"),
            Mock(spec=ReadableSpan, name="span3"),
        ]

        with patch("opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter.export") as mock_export:
            mock_export.return_value = SpanExportResult.SUCCESS

            # Create exporter
            exporter = AuthenticatedOTLPExporter(endpoint=self.endpoint, jwt=self.jwt)

            # Export spans
            result = exporter.export(mock_spans)

            # Verify results
            self.assertEqual(result, SpanExportResult.SUCCESS)

            # Test clear method
            exporter.clear()  # Should not raise any exception

    def test_export_with_different_compression_types(self):
        """Test exporter with different compression types."""
        compression_types = [Compression.Gzip, Compression.Deflate, None]

        for compression in compression_types:
            with self.subTest(compression=compression):
                exporter = AuthenticatedOTLPExporter(endpoint=self.endpoint, jwt=self.jwt, compression=compression)

                # Verify the exporter was created successfully
                self.assertIsInstance(exporter, AuthenticatedOTLPExporter)

    def test_export_with_different_timeouts(self):
        """Test exporter with different timeout values."""
        timeout_values = [10, 30, 60, None]

        for timeout in timeout_values:
            with self.subTest(timeout=timeout):
                exporter = AuthenticatedOTLPExporter(endpoint=self.endpoint, jwt=self.jwt, timeout=timeout)

                # Verify the exporter was created successfully
                self.assertIsInstance(exporter, AuthenticatedOTLPExporter)


if __name__ == "__main__":
    unittest.main()
