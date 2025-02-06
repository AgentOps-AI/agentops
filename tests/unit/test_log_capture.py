import logging
import sys
from io import StringIO
from unittest.mock import patch
from uuid import uuid4

import pytest
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, ConsoleLogExporter
from opentelemetry.sdk.resources import Resource
from rich.console import Console

from agentops.log_config import logger as agentops_logger
from agentops.log_capture import LogCapture


@pytest.fixture
def session_id():
    return uuid4()


@pytest.fixture
def mock_session(session_id, logger_provider):
    """Create a mock session with logging components"""

    class MockSession:
        def __init__(self, session_id, logger_provider):
            self.session_id = session_id
            self._log_handler = LoggingHandler(
                level=logging.INFO,
                logger_provider=logger_provider,
            )
            # Add handler to logger
            agentops_logger.addHandler(self._log_handler)

        def cleanup(self):
            # Remove handler from logger
            agentops_logger.removeHandler(self._log_handler)

    return MockSession(session_id, logger_provider)


@pytest.fixture
def logger_provider():
    """Set up OpenTelemetry logging"""
    resource = Resource.create(
        {
            "service.name": "test-service",
        }
    )
    provider = LoggerProvider(resource=resource)
    exporter = ConsoleLogExporter()
    provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
    return provider


@pytest.fixture
def capture(session_id, mock_session):
    """Set up LogCapture with OpenTelemetry logging"""
    # Mock the session registry to return our mock session
    with patch("agentops.session.get_active_sessions", return_value=[mock_session]):
        capture = LogCapture(session_id=session_id)
        yield capture

    # Clean up
    mock_session.cleanup()


def test_basic_stdout_capture(capture):
    """Test capturing basic stdout output"""
    test_output = "Hello, world!"

    capture.start()
    try:
        print(test_output)
    finally:
        capture.stop()

    assert capture.stdout_line_count == 1
    assert capture.stderr_line_count == 0
    assert capture.log_level_counts["INFO"] == 1
    assert not capture.is_capturing


def test_basic_stderr_capture(capture):
    """Test capturing basic stderr output"""
    test_error = "Error message"

    capture.start()
    try:
        sys.stderr.write(test_error + "\n")
    finally:
        capture.stop()

    assert capture.stdout_line_count == 0
    assert capture.stderr_line_count == 1
    assert capture.log_level_counts["ERROR"] == 1


def test_rich_color_capture(capture):
    """Test capturing Rich colored output"""
    capture.start()
    try:
        console = Console(force_terminal=True)
        console.print("[red]Colored[/red] text")
    finally:
        capture.stop()

    assert capture.stdout_line_count == 1
    assert capture.log_level_counts["INFO"] == 1


def test_ansi_color_capture(capture):
    """Test capturing raw ANSI colored output"""
    capture.start()
    try:
        print("\033[31mRed\033[0m text")
        sys.stderr.write("\033[34mBlue\033[0m error\n")
    finally:
        capture.stop()

    assert capture.stdout_line_count == 1
    assert capture.stderr_line_count == 1
    assert capture.log_level_counts["INFO"] == 1
    assert capture.log_level_counts["ERROR"] == 1


def test_span_data_transformation(capture, session_id):
    """Test converting log capture to span data"""
    capture.start()
    try:
        print("Info message")
        sys.stderr.write("Error message\n")
    finally:
        capture.stop()

    span_data = capture.to_span_data()

    # Check basic attributes
    assert span_data["session.id"] == str(session_id)
    assert span_data["log.stdout_count"] == 1
    assert span_data["log.stderr_count"] == 1
    assert span_data["log.is_capturing"] is False

    # Check log level counts
    assert span_data["log.level.info"] == 1
    assert span_data["log.level.error"] == 1

    # Check timing data
    assert "log.start_time" in span_data
    assert "log.end_time" in span_data
    assert "log.duration_seconds" in span_data
    assert span_data["log.duration_seconds"] > 0


def test_empty_lines_ignored(capture):
    """Test that empty lines are not counted"""
    capture.start()
    try:
        print("")
        print("\n")
        print("   ")
        sys.stderr.write("\n")
    finally:
        capture.stop()

    assert capture.stdout_line_count == 0
    assert capture.stderr_line_count == 0
    assert sum(capture.log_level_counts.values()) == 0


def test_multiple_captures(capture):
    """Test starting and stopping capture multiple times"""
    # First capture
    capture.start()
    print("First")
    capture.stop()

    assert capture.stdout_line_count == 1

    # Second capture
    capture.start()
    print("Second")
    sys.stderr.write("Error\n")
    capture.stop()

    assert capture.stdout_line_count == 2
    assert capture.stderr_line_count == 1


def test_session_not_found():
    """Test that starting capture without a session raises an error"""
    session_id = uuid4()

    # Create LogCapture without mocking session registry
    capture = LogCapture(session_id=session_id)

    with pytest.raises(ValueError, match=f"No active session found with ID {session_id}"):
        capture.start()
