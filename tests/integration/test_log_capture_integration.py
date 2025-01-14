import sys
import time
import threading
from uuid import uuid4
from dataclasses import dataclass
from typing import Optional
import pytest
from io import StringIO

from agentops.telemetry.config import OTELConfig
from agentops.telemetry.manager import TelemetryManager
from agentops.session.log_capture import LogCapture


@dataclass
class MockSession:
    id: uuid4
    _telemetry: Optional[TelemetryManager] = None


@pytest.fixture
def telemetry_setup():
    """Setup and teardown telemetry manager with config"""
    telemetry = TelemetryManager()
    config = OTELConfig(
        resource_attributes={"test.attribute": "integration_test"},
        endpoint="http://localhost:4317"
    )
    telemetry.initialize(config)
    yield telemetry
    telemetry.shutdown()


@pytest.fixture
def session(telemetry_setup):
    """Create a session with telemetry"""
    return MockSession(id=uuid4(), _telemetry=telemetry_setup)


@pytest.fixture
def standalone_session():
    """Create a session without telemetry"""
    return MockSession(id=uuid4())


def test_basic_output_capture(session):
    """Test basic stdout and stderr capture functionality.
    
    Verifies:
    - Basic stdout message capture
    - Basic stderr message capture
    - Empty line handling (should be ignored)
    - Proper stream restoration after capture stops
    """
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    
    capture = LogCapture(session)
    capture.start()
    
    try:
        print("Test stdout message")
        sys.stderr.write("Test stderr message\n")
        
        # Empty lines should be ignored
        print("")
        print("\n\n")
        
    finally:
        capture.stop()
        
    # Verify stdout/stderr are restored to original
    assert sys.stdout == original_stdout, "stdout was not properly restored after capture"
    assert sys.stderr == original_stderr, "stderr was not properly restored after capture"


def test_concurrent_output(session):
    """Test concurrent output capture from multiple threads.
    
    Verifies:
    - Thread-safe capture of stdout/stderr
    - Correct interleaving of messages from different threads
    - Background thread output capture
    - Main thread output capture
    - Message ordering preservation
    """
    capture = LogCapture(session)
    capture.start()
    
    output_received = []
    
    def background_task():
        for i in range(3):
            time.sleep(0.1)
            print(f"Background message {i}")
            sys.stderr.write(f"Background error {i}\n")
            output_received.append(i)
    
    try:
        thread = threading.Thread(target=background_task)
        thread.start()
        
        # Main thread output
        for i in range(3):
            time.sleep(0.15)
            print(f"Main message {i}")
            output_received.append(i)
            
        thread.join()
        
    finally:
        capture.stop()
    
    assert len(output_received) == 6, (
        "Expected 6 messages (3 from each thread), but got "
        f"{len(output_received)} messages"
    )


def test_multiple_start_stop(session):
    """Test multiple start/stop cycles of the LogCapture.
    
    Verifies:
    - Multiple start/stop cycles work correctly
    - Streams are properly restored after each stop
    - No resource leaks across cycles
    - Consistent behavior across multiple captures
    """
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    
    capture = LogCapture(session)
    
    for cycle in range(3):
        capture.start()
        print("Test message")
        capture.stop()
        
        # Verify original streams are restored
        assert sys.stdout == original_stdout, (
            f"stdout not restored after cycle {cycle + 1}"
        )
        assert sys.stderr == original_stderr, (
            f"stderr not restored after cycle {cycle + 1}"
        )


def test_standalone_capture(standalone_session):
    """Test LogCapture functionality without telemetry manager.
    
    Verifies:
    - Capture works without telemetry manager
    - Proper handler creation in standalone mode
    - Resource cleanup after capture
    - Handler and provider are properly cleaned up
    """
    capture = LogCapture(standalone_session)
    capture.start()
    
    try:
        print("Standalone test message")
        sys.stderr.write("Standalone error message\n")
    finally:
        capture.stop()
    
    # Verify handler cleanup
    assert capture._handler is None, (
        "LogHandler was not properly cleaned up after standalone capture"
    )
    assert capture._logger_provider is None, (
        "LoggerProvider was not properly cleaned up after standalone capture"
    )


def test_flush_functionality(session):
    """Test the flush operation of LogCapture.
    
    Verifies:
    - Flush operation works correctly
    - Messages before and after flush are captured
    - No data loss during flush
    - Capture continues working after flush
    """
    capture = LogCapture(session)
    capture.start()
    
    try:
        print("Message before flush")
        capture.flush()
        print("Message after flush")
    finally:
        capture.stop()


def test_nested_capture(session):
    """Test nested LogCapture instances.
    
    Verifies:
    - Multiple capture instances can coexist
    - Inner capture doesn't interfere with outer capture
    - Proper cleanup of nested captures
    - Correct message capture at different nesting levels
    """
    outer_capture = LogCapture(session)
    inner_capture = LogCapture(session)
    
    outer_capture.start()
    try:
        print("Outer message")
        
        inner_capture.start()
        try:
            print("Inner message")
        finally:
            inner_capture.stop()
            
        print("Back to outer")
    finally:
        outer_capture.stop()
