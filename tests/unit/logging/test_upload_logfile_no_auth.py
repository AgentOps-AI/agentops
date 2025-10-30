import builtins
import pytest
from unittest.mock import patch, MagicMock
from agentops.logging.instrument_logging import setup_print_logger, upload_logfile


@pytest.fixture
def reset_print():
    """Fixture to reset the print function after tests"""
    original_print = builtins.print
    yield
    builtins.print = original_print


def test_upload_logfile_skips_when_no_auth_token(reset_print):
    """Test that upload_logfile skips upload gracefully when auth token is not set."""
    setup_print_logger()
    test_message = "Test upload message"
    print(test_message)

    mock_client = MagicMock()
    mock_client.api.v4.auth_token = None

    with patch("agentops.get_client", return_value=mock_client):
        upload_logfile(trace_id=123)
        mock_client.api.v4.upload_logfile.assert_not_called()


def test_upload_logfile_uploads_when_auth_token_is_set(reset_print):
    """Test that upload_logfile uploads when auth token is set."""
    setup_print_logger()
    test_message = "Test upload message"
    print(test_message)

    mock_client = MagicMock()
    mock_client.api.v4.auth_token = "test_token"

    with patch("agentops.get_client", return_value=mock_client):
        upload_logfile(trace_id=123)
        mock_client.api.v4.upload_logfile.assert_called_once()
