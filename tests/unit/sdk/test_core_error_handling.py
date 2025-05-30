"""
Tests for TracingCore error handling improvements.

This module tests the enhanced error handling in TracingCore._flush_span_processors()
that was added to provide comprehensive exception handling for different failure scenarios.
"""

from unittest.mock import MagicMock, patch

from agentops.sdk.core import TracingCore


class TestTracingCoreFlushErrorHandling:
    """Tests for the enhanced _flush_span_processors error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tracing_core = TracingCore.get_instance()
        # Reset state for each test
        self.tracing_core._initialized = False
        self.tracing_core._provider = None

    @patch("agentops.sdk.core.logger")
    def test_flush_no_provider(self, mock_logger):
        """Test _flush_span_processors when no provider is available."""
        # Ensure no provider is set
        self.tracing_core._provider = None

        # Call flush
        self.tracing_core._flush_span_processors()

        # Verify debug message was logged
        mock_logger.debug.assert_called_once_with("No provider available for force_flush.")

    @patch("agentops.sdk.core.logger")
    def test_flush_provider_without_force_flush_method(self, mock_logger):
        """Test _flush_span_processors when provider doesn't support force_flush."""
        # Create a mock provider without force_flush method
        mock_provider = MagicMock()
        del mock_provider.force_flush  # Remove the method
        self.tracing_core._provider = mock_provider

        # Call flush
        self.tracing_core._flush_span_processors()

        # Verify debug message was logged
        mock_logger.debug.assert_called_once_with("Provider does not support force_flush.")

    @patch("agentops.sdk.core.logger")
    def test_flush_successful(self, mock_logger):
        """Test _flush_span_processors with successful flush."""
        # Create a mock provider with force_flush method
        mock_provider = MagicMock()
        mock_provider.force_flush.return_value = True
        self.tracing_core._provider = mock_provider

        # Call flush
        self.tracing_core._flush_span_processors()

        # Verify force_flush was called
        mock_provider.force_flush.assert_called_once()

        # Verify success messages were logged
        expected_calls = [
            ("debug", "Attempting to force flush span processors..."),
            ("debug", "Provider force_flush completed successfully."),
        ]

        actual_calls = [(call[0], call[1][0]) for call in mock_logger.method_calls]
        for level, message in expected_calls:
            assert (level, message) in actual_calls

    @patch("agentops.sdk.core.logger")
    def test_flush_attribute_error(self, mock_logger):
        """Test _flush_span_processors when AttributeError is raised."""
        # Create a mock provider where force_flush raises AttributeError
        mock_provider = MagicMock()
        mock_provider.force_flush.side_effect = AttributeError("force_flush method not available")
        self.tracing_core._provider = mock_provider

        # Call flush - should not raise exception
        self.tracing_core._flush_span_processors()

        # Verify force_flush was attempted
        mock_provider.force_flush.assert_called_once()

        # Verify warning was logged
        mock_logger.warning.assert_called_once_with(
            "Provider force_flush method not available: force_flush method not available"
        )

    @patch("agentops.sdk.core.logger")
    def test_flush_runtime_error(self, mock_logger):
        """Test _flush_span_processors when RuntimeError is raised."""
        # Create a mock provider where force_flush raises RuntimeError
        mock_provider = MagicMock()
        mock_provider.force_flush.side_effect = RuntimeError("Provider is shutting down")
        self.tracing_core._provider = mock_provider

        # Call flush - should not raise exception
        self.tracing_core._flush_span_processors()

        # Verify force_flush was attempted
        mock_provider.force_flush.assert_called_once()

        # Verify warning was logged
        mock_logger.warning.assert_called_once_with(
            "Runtime error during force_flush (provider may be shutting down): Provider is shutting down"
        )

    @patch("agentops.sdk.core.logger")
    def test_flush_unexpected_exception(self, mock_logger):
        """Test _flush_span_processors when unexpected exception is raised."""
        # Create a mock provider where force_flush raises unexpected exception
        mock_provider = MagicMock()
        mock_provider.force_flush.side_effect = ValueError("Unexpected error")
        self.tracing_core._provider = mock_provider

        # Call flush - should not raise exception
        self.tracing_core._flush_span_processors()

        # Verify force_flush was attempted
        mock_provider.force_flush.assert_called_once()

        # Verify error was logged with exc_info
        mock_logger.error.assert_called_once_with(
            "Unexpected error during force_flush: Unexpected error", exc_info=True
        )

    @patch("agentops.sdk.core.logger")
    def test_flush_multiple_exception_types(self, mock_logger):
        """Test that different exception types are handled with appropriate log levels."""
        test_cases = [
            (AttributeError("attr error"), "warning", "Provider force_flush method not available: attr error"),
            (
                RuntimeError("runtime error"),
                "warning",
                "Runtime error during force_flush (provider may be shutting down): runtime error",
            ),
            (ValueError("value error"), "error", "Unexpected error during force_flush: value error"),
            (TypeError("type error"), "error", "Unexpected error during force_flush: type error"),
            (Exception("generic error"), "error", "Unexpected error during force_flush: generic error"),
        ]

        for exception, expected_level, expected_message in test_cases:
            # Reset mock
            mock_logger.reset_mock()

            # Create a mock provider that raises the specific exception
            mock_provider = MagicMock()
            mock_provider.force_flush.side_effect = exception
            self.tracing_core._provider = mock_provider

            # Call flush - should not raise exception
            self.tracing_core._flush_span_processors()

            # Verify the appropriate log level was used
            if expected_level == "warning":
                mock_logger.warning.assert_called_once_with(expected_message)
                mock_logger.error.assert_not_called()
            elif expected_level == "error":
                mock_logger.error.assert_called_once_with(expected_message, exc_info=True)
                mock_logger.warning.assert_not_called()

    @patch("agentops.sdk.core.logger")
    def test_flush_graceful_degradation(self, mock_logger):
        """Test that flush failures don't break the application."""
        # Create a mock provider that always fails
        mock_provider = MagicMock()
        mock_provider.force_flush.side_effect = Exception("Always fails")
        self.tracing_core._provider = mock_provider

        # Call flush multiple times - should never raise exception
        for _ in range(3):
            self.tracing_core._flush_span_processors()

        # Verify force_flush was attempted each time
        assert mock_provider.force_flush.call_count == 3

        # Verify errors were logged each time
        assert mock_logger.error.call_count == 3

    @patch("agentops.sdk.core.logger")
    def test_flush_hasattr_check_behavior(self, mock_logger):
        """Test the hasattr check behavior for force_flush method."""
        # Test case 1: Provider without force_flush attribute
        mock_provider = MagicMock()
        del mock_provider.force_flush  # Remove the attribute completely
        self.tracing_core._provider = mock_provider

        # This should trigger the hasattr check and log debug message
        self.tracing_core._flush_span_processors()

        # When provider doesn't have force_flush attribute, it should only log the "does not support" message
        mock_logger.debug.assert_called_once_with("Provider does not support force_flush.")

        # Reset for next test
        mock_logger.reset_mock()

        # Test case 2: Provider has callable force_flush
        mock_provider = MagicMock()
        mock_provider.force_flush = MagicMock(return_value=True)
        self.tracing_core._provider = mock_provider

        self.tracing_core._flush_span_processors()

        # Should attempt to call force_flush
        mock_provider.force_flush.assert_called_once()

    @patch("agentops.sdk.core.logger")
    def test_flush_logging_sequence(self, mock_logger):
        """Test the complete logging sequence during successful flush."""
        # Create a mock provider with force_flush method
        mock_provider = MagicMock()
        mock_provider.force_flush.return_value = True
        self.tracing_core._provider = mock_provider

        # Call flush
        self.tracing_core._flush_span_processors()

        # Verify the complete logging sequence
        expected_debug_calls = [
            "Attempting to force flush span processors...",
            "Provider force_flush completed successfully.",
        ]

        debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]
        assert debug_calls == expected_debug_calls

    @patch("agentops.sdk.core.logger")
    def test_flush_provider_none_vs_no_method(self, mock_logger):
        """Test distinction between no provider and provider without method."""
        # Test 1: No provider
        self.tracing_core._provider = None
        self.tracing_core._flush_span_processors()

        mock_logger.debug.assert_called_with("No provider available for force_flush.")
        mock_logger.reset_mock()

        # Test 2: Provider without force_flush method
        mock_provider = MagicMock()
        del mock_provider.force_flush
        self.tracing_core._provider = mock_provider

        self.tracing_core._flush_span_processors()

        mock_logger.debug.assert_called_with("Provider does not support force_flush.")


class TestTracingCoreFlushIntegration:
    """Integration tests for TracingCore flush functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tracing_core = TracingCore.get_instance()
        # Reset state for each test
        self.tracing_core._initialized = False
        self.tracing_core._provider = None

    @patch("agentops.sdk.core.logger")
    def test_flush_called_during_shutdown(self, mock_logger):
        """Test that _flush_span_processors is called during shutdown."""
        # Create a mock provider
        mock_provider = MagicMock()
        mock_provider.force_flush.return_value = True
        self.tracing_core._provider = mock_provider
        self.tracing_core._initialized = True

        # Mock the shutdown method to track flush calls
        with patch.object(self.tracing_core, "_flush_span_processors") as mock_flush:
            # Call shutdown
            self.tracing_core.shutdown()

            # Verify flush was called
            mock_flush.assert_called_once()

    @patch("agentops.sdk.core.logger")
    def test_flush_resilience_during_shutdown(self, mock_logger):
        """Test that shutdown continues even if flush fails."""
        # Create a mock provider that fails on flush
        mock_provider = MagicMock()
        mock_provider.force_flush.side_effect = Exception("Flush failed")
        mock_provider.shutdown.return_value = None
        self.tracing_core._provider = mock_provider
        self.tracing_core._initialized = True

        # Shutdown should complete successfully despite flush failure
        self.tracing_core.shutdown()

        # Verify provider shutdown was still called
        mock_provider.shutdown.assert_called_once()

        # Verify error was logged
        mock_logger.error.assert_called_once_with("Unexpected error during force_flush: Flush failed", exc_info=True)

    @patch("agentops.sdk.core.logger")
    def test_flush_with_real_provider_interface(self, mock_logger):
        """Test flush with a more realistic provider mock."""
        # Create a mock provider that mimics real TracerProvider interface
        mock_provider = MagicMock()
        mock_provider.force_flush = MagicMock(return_value=True)

        # Add other typical provider methods
        mock_provider.get_tracer = MagicMock()
        mock_provider.shutdown = MagicMock()

        self.tracing_core._provider = mock_provider

        # Call flush
        self.tracing_core._flush_span_processors()

        # Verify only force_flush was called, not other methods
        mock_provider.force_flush.assert_called_once()
        mock_provider.get_tracer.assert_not_called()
        mock_provider.shutdown.assert_not_called()


class TestTracingCoreFlushBackwardCompatibility:
    """Tests to ensure flush error handling doesn't break existing functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tracing_core = TracingCore.get_instance()
        # Reset state for each test
        self.tracing_core._initialized = False
        self.tracing_core._provider = None

    def test_flush_preserves_existing_behavior(self):
        """Test that flush behavior is preserved for existing code."""
        # Create a mock provider
        mock_provider = MagicMock()
        mock_provider.force_flush.return_value = True
        self.tracing_core._provider = mock_provider

        # Call flush - should not raise any exceptions
        self.tracing_core._flush_span_processors()

        # Verify force_flush was called
        mock_provider.force_flush.assert_called_once()

    def test_flush_method_signature_unchanged(self):
        """Test that _flush_span_processors method signature is unchanged."""
        # This test ensures the method can still be called without parameters
        import inspect

        signature = inspect.signature(self.tracing_core._flush_span_processors)

        # Should have no required parameters
        assert len(signature.parameters) == 0

        # Should be callable without arguments
        self.tracing_core._provider = None
        self.tracing_core._flush_span_processors()  # Should not raise
