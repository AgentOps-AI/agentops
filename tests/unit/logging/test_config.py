import os
import logging
import pytest
from unittest.mock import patch, MagicMock, mock_open
from agentops.logging.config import configure_logging, intercept_opentelemetry_logging, logger


class TestConfigureLogging:
    """Test the configure_logging function"""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test"""
        # Store original logger state
        original_handlers = logger.handlers[:]
        original_level = logger.level

        yield

        # Restore original logger state
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        for handler in original_handlers:
            logger.addHandler(handler)
        logger.setLevel(original_level)

    def test_configure_logging_with_no_config(self):
        """Test configure_logging when no config is provided"""
        with patch("agentops.config.Config") as mock_config_class:
            mock_config = MagicMock()
            mock_config.log_level = logging.INFO
            mock_config_class.return_value = mock_config

            result = configure_logging()

            assert result == logger
            assert logger.level == logging.INFO
            assert len(logger.handlers) >= 1  # At least console handler

    def test_configure_logging_with_config_object(self):
        """Test configure_logging with a provided config object"""
        mock_config = MagicMock()
        mock_config.log_level = logging.DEBUG

        result = configure_logging(mock_config)

        assert result == logger
        assert logger.level == logging.DEBUG

    def test_configure_logging_with_env_override(self):
        """Test configure_logging with environment variable override"""
        with patch.dict(os.environ, {"AGENTOPS_LOG_LEVEL": "WARNING"}):
            mock_config = MagicMock()
            mock_config.log_level = logging.DEBUG

            result = configure_logging(mock_config)

            assert result == logger
            assert logger.level == logging.WARNING

    def test_configure_logging_with_invalid_env_level(self):
        """Test configure_logging with invalid environment log level"""
        with patch.dict(os.environ, {"AGENTOPS_LOG_LEVEL": "INVALID_LEVEL"}):
            mock_config = MagicMock()
            mock_config.log_level = logging.DEBUG

            result = configure_logging(mock_config)

            assert result == logger
            assert logger.level == logging.DEBUG  # Falls back to config

    def test_configure_logging_with_string_config_level(self):
        """Test configure_logging with string log level in config"""
        mock_config = MagicMock()
        mock_config.log_level = "ERROR"

        result = configure_logging(mock_config)

        assert result == logger
        assert logger.level == logging.ERROR

    def test_configure_logging_with_invalid_string_config_level(self):
        """Test configure_logging with invalid string log level in config"""
        mock_config = MagicMock()
        mock_config.log_level = "INVALID_LEVEL"

        result = configure_logging(mock_config)

        assert result == logger
        assert logger.level == logging.INFO  # Falls back to INFO

    def test_configure_logging_with_non_string_int_config_level(self):
        """Test configure_logging with non-string, non-int log level in config"""
        mock_config = MagicMock()
        mock_config.log_level = None  # Neither string nor int

        result = configure_logging(mock_config)

        assert result == logger
        assert logger.level == logging.INFO  # Falls back to INFO

    def test_configure_logging_removes_existing_handlers(self):
        """Test that configure_logging removes existing handlers"""
        # Add a dummy handler
        dummy_handler = logging.StreamHandler()
        logger.addHandler(dummy_handler)
        assert len(logger.handlers) >= 1

        mock_config = MagicMock()
        mock_config.log_level = logging.INFO

        configure_logging(mock_config)

        # Check that the dummy handler was removed
        assert dummy_handler not in logger.handlers

    def test_configure_logging_creates_console_handler(self):
        """Test that configure_logging creates a console handler"""
        mock_config = MagicMock()
        mock_config.log_level = logging.INFO

        configure_logging(mock_config)

        # Check that we have at least one StreamHandler
        stream_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
        assert len(stream_handlers) >= 1

    @patch("builtins.open", new_callable=mock_open)
    def test_configure_logging_with_file_logging_enabled(self, mock_file):
        """Test configure_logging with file logging enabled"""
        with patch.dict(os.environ, {"AGENTOPS_LOGGING_TO_FILE": "true"}):
            mock_config = MagicMock()
            mock_config.log_level = logging.INFO

            configure_logging(mock_config)

            # Check that file handler was created
            file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
            assert len(file_handlers) >= 1
            # Check that open was called with the correct filename (path may be absolute)
            mock_file.assert_called_once()
            call_args = mock_file.call_args
            assert call_args[0][0].endswith("agentops.log")
            assert call_args[0][1] == "w"

    def test_configure_logging_with_file_logging_disabled(self):
        """Test configure_logging with file logging disabled"""
        with patch.dict(os.environ, {"AGENTOPS_LOGGING_TO_FILE": "false"}):
            mock_config = MagicMock()
            mock_config.log_level = logging.INFO

            configure_logging(mock_config)

            # Check that no file handler was created
            file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
            assert len(file_handlers) == 0

    def test_configure_logging_with_file_logging_case_insensitive(self):
        """Test configure_logging with file logging case insensitive"""
        with patch.dict(os.environ, {"AGENTOPS_LOGGING_TO_FILE": "TRUE"}):
            mock_config = MagicMock()
            mock_config.log_level = logging.INFO

            configure_logging(mock_config)

            # Check that file handler was created
            file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
            assert len(file_handlers) >= 1

    def test_configure_logging_with_file_logging_default(self):
        """Test configure_logging with file logging default (no env var)"""
        # Remove the env var if it exists
        if "AGENTOPS_LOGGING_TO_FILE" in os.environ:
            del os.environ["AGENTOPS_LOGGING_TO_FILE"]

        with patch("builtins.open", new_callable=mock_open):
            mock_config = MagicMock()
            mock_config.log_level = logging.INFO

            configure_logging(mock_config)

            # Check that file handler was created (default is True)
            file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
            assert len(file_handlers) >= 1


class TestInterceptOpenTelemetryLogging:
    """Test the intercept_opentelemetry_logging function"""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test"""
        # Store original opentelemetry logger state
        otel_logger = logging.getLogger("opentelemetry")
        original_handlers = otel_logger.handlers[:]
        original_level = otel_logger.level
        original_propagate = otel_logger.propagate

        yield

        # Restore original opentelemetry logger state
        for handler in otel_logger.handlers[:]:
            otel_logger.removeHandler(handler)
        for handler in original_handlers:
            otel_logger.addHandler(handler)
        otel_logger.setLevel(original_level)
        otel_logger.propagate = original_propagate

    def test_intercept_opentelemetry_logging_configures_logger(self):
        """Test that intercept_opentelemetry_logging configures the opentelemetry logger"""
        intercept_opentelemetry_logging()

        otel_logger = logging.getLogger("opentelemetry")
        assert otel_logger.level == logging.DEBUG
        assert not otel_logger.propagate
        assert len(otel_logger.handlers) == 1

    def test_intercept_opentelemetry_logging_removes_existing_handlers(self):
        """Test that intercept_opentelemetry_logging removes existing handlers"""
        otel_logger = logging.getLogger("opentelemetry")
        dummy_handler = logging.StreamHandler()
        otel_logger.addHandler(dummy_handler)

        intercept_opentelemetry_logging()

        assert dummy_handler not in otel_logger.handlers

    def test_intercept_opentelemetry_logging_creates_custom_handler(self):
        """Test that intercept_opentelemetry_logging creates a custom handler"""
        intercept_opentelemetry_logging()

        otel_logger = logging.getLogger("opentelemetry")
        assert len(otel_logger.handlers) == 1

        handler = otel_logger.handlers[0]
        assert hasattr(handler, "emit")

    def test_otel_log_handler_emit_with_opentelemetry_prefix(self):
        """Test the OtelLogHandler.emit method with opentelemetry prefix"""
        intercept_opentelemetry_logging()

        otel_logger = logging.getLogger("opentelemetry")
        handler = otel_logger.handlers[0]

        # Create a mock record with opentelemetry prefix
        record = logging.LogRecord(
            name="opentelemetry.trace",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        with patch.object(logger, "debug") as mock_debug:
            handler.emit(record)
            mock_debug.assert_called_once_with("[opentelemetry.trace] Test message")

    def test_otel_log_handler_emit_without_opentelemetry_prefix(self):
        """Test the OtelLogHandler.emit method without opentelemetry prefix"""
        intercept_opentelemetry_logging()

        otel_logger = logging.getLogger("opentelemetry")
        handler = otel_logger.handlers[0]

        # Create a mock record without opentelemetry prefix
        record = logging.LogRecord(
            name="some.other.module",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        with patch.object(logger, "debug") as mock_debug:
            handler.emit(record)
            mock_debug.assert_called_once_with("[opentelemetry.some.other.module] Test message")

    def test_otel_log_handler_emit_with_exact_opentelemetry_name(self):
        """Test the OtelLogHandler.emit method with exact 'opentelemetry' name"""
        intercept_opentelemetry_logging()

        otel_logger = logging.getLogger("opentelemetry")
        handler = otel_logger.handlers[0]

        # Create a mock record with exact 'opentelemetry' name
        record = logging.LogRecord(
            name="opentelemetry", level=logging.INFO, pathname="", lineno=0, msg="Test message", args=(), exc_info=None
        )

        with patch.object(logger, "debug") as mock_debug:
            handler.emit(record)
            mock_debug.assert_called_once_with("[opentelemetry.opentelemetry] Test message")


class TestLoggerInitialization:
    """Test the logger initialization at module level"""

    def test_logger_initialization(self):
        """Test that the logger is properly initialized"""
        assert logger.name == "agentops"
        assert not logger.propagate
        assert logger.level == logging.CRITICAL  # Default level
