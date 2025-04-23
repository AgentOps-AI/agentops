import os
import builtins
import pytest
from unittest.mock import patch, MagicMock
from agentops.logging.instrument_logging import setup_print_logger, upload_logfile, LOGFILE_NAME
import logging

@pytest.fixture
def cleanup_log_file():
    """Fixture to clean up the log file before and after tests"""
    log_file = os.path.join(os.getcwd(), LOGFILE_NAME)
    if os.path.exists(log_file):
        os.remove(log_file)
    yield
    if os.path.exists(log_file):
        os.remove(log_file)

def test_setup_print_logger_creates_log_file(cleanup_log_file):
    """Test that setup_print_logger creates a log file"""
    setup_print_logger()
    log_file = os.path.join(os.getcwd(), LOGFILE_NAME)
    assert os.path.exists(log_file)

def test_print_logger_writes_to_file(cleanup_log_file):
    """Test that the monkeypatched print function writes to the log file"""
    setup_print_logger()
    test_message = "Test log message"
    print(test_message)
    
    log_file = os.path.join(os.getcwd(), LOGFILE_NAME)
    with open(log_file, 'r') as f:
        log_content = f.read()
        assert test_message in log_content

def test_print_logger_preserves_original_print(cleanup_log_file):
    """Test that the original print function is preserved"""
    original_print = builtins.print
    setup_print_logger()
    assert builtins.print != original_print
    
    # Cleanup should restore original print
    for handler in logging.getLogger('agentops_file_logger').handlers[:]:
        handler.close()
        logging.getLogger('agentops_file_logger').removeHandler(handler)
    builtins.print = original_print

@patch('agentops.get_client')
def test_upload_logfile(mock_get_client, cleanup_log_file):
    """Test that upload_logfile reads and uploads log content"""
    # Setup
    setup_print_logger()
    test_message = "Test upload message"
    print(test_message)
    
    # Mock the client
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    # Test upload
    upload_logfile(trace_id=123)
    
    # Verify
    mock_client.api.v4.upload_logfile.assert_called_once()
    assert not os.path.exists(os.path.join(os.getcwd(), LOGFILE_NAME))

def test_upload_logfile_nonexistent_file():
    """Test that upload_logfile handles nonexistent log file gracefully"""
    with patch('agentops.get_client') as mock_get_client:
        upload_logfile(trace_id=123)
        mock_get_client.assert_not_called() 