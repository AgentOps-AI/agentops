import builtins
import pytest
from unittest.mock import patch, MagicMock
from agentops.logging.instrument_logging import setup_print_logger, upload_logfile
import logging


@pytest.fixture
def reset_print():
    """Fixture to reset the print function after tests"""
    original_print = builtins.print
    yield
    builtins.print = original_print


def test_setup_print_logger_creates_buffer_logger_and_handler():
    """Test that setup_print_logger creates a buffer logger with a StreamHandler."""
    setup_print_logger()
    buffer_logger = logging.getLogger("agentops_buffer_logger")
    assert buffer_logger.level == logging.DEBUG
    assert len(buffer_logger.handlers) == 1
    assert isinstance(buffer_logger.handlers[0], logging.StreamHandler)


def test_print_logger_writes_message_to_stringio_buffer(reset_print):
    """Test that the monkeypatched print function writes messages to the StringIO buffer."""
    setup_print_logger()
    test_message = "Test log message"
    print(test_message)
    buffer_logger = logging.getLogger("agentops_buffer_logger")
    log_content = buffer_logger.handlers[0].stream.getvalue()
    assert test_message in log_content


def test_print_logger_replaces_and_restores_builtin_print(reset_print):
    """Test that setup_print_logger replaces builtins.print and the fixture restores it after the test."""
    import agentops.logging.instrument_logging as il

    builtins.print = il._original_print
    original_print = builtins.print
    setup_print_logger()
    assert builtins.print != original_print
    # The reset_print fixture will restore print after the test


@patch("agentops.get_client")
def test_upload_logfile_sends_buffer_content_and_clears_buffer(mock_get_client):
    """Test that upload_logfile uploads the buffer content and clears the buffer after upload."""
    setup_print_logger()
    test_message = "Test upload message"
    print(test_message)
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    upload_logfile(trace_id=123)
    mock_client.api.v4.upload_logfile.assert_called_once()
    buffer_logger = logging.getLogger("agentops_buffer_logger")
    assert buffer_logger.handlers[0].stream.getvalue() == ""


def test_upload_logfile_does_nothing_when_buffer_is_empty():
    """Test that upload_logfile does nothing and does not call the client when the buffer is empty."""
    with patch("agentops.get_client") as mock_get_client:
        upload_logfile(trace_id=123)
        mock_get_client.assert_not_called()
