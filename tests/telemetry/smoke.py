import time
import uuid
from dataclasses import dataclass

import pytest

from agentops.config import Configuration
from agentops.telemetry.manager import OTELManager
from agentops.telemetry.processor import EventProcessor
from agentops.telemetry.exporter import ExportManager
from agentops.telemetry.metrics import TelemetryMetrics

@dataclass
class TestEvent:
    """Simple test event for smoke testing"""
    id: uuid.UUID = uuid.uuid4()
    event_type: str = "test_event"
    init_timestamp: str | None = None
    end_timestamp: str | None = None
    data: dict | None = None

def test_basic_telemetry_flow():
    """Test the basic flow of events through the telemetry system"""
    # Setup
    config = Configuration(api_key="test-key")
    session_id = uuid.uuid4()
    
    # Initialize components
    manager = OTELManager(config)
    provider = manager.initialize("test-service", str(session_id))
    tracer = manager.get_tracer("test-tracer")
    
    exporter = ExportManager(
        session_id=session_id,
        endpoint="http://localhost:8000/v2/create_events",
        jwt="test-jwt",
        api_key="test-key"
    )
    
    processor = EventProcessor(session_id, tracer)
    
    # Create and process a test event
    event = TestEvent(data={"test": "data"})
    span = processor.process_event(event, tags=["test"])
    
    # Verify event was processed
    assert span is not None
    assert processor.event_counts["test_event"] == 1

def test_metrics_collection():
    """Test basic metrics collection"""
    metrics = TelemetryMetrics("test-service")
    
    # Record some test metrics
    metrics.record_export_attempt(True, 100.0, 10)
    metrics.record_export_attempt(False, 200.0, 5)
    
    # Let metrics flush (they're async)
    time.sleep(0.1)
    
    # Cleanup
    metrics.shutdown()

def test_manager_lifecycle():
    """Test OTEL manager lifecycle (init -> shutdown)"""
    config = Configuration(api_key="test-key")
    manager = OTELManager(config)
    
    # Initialize
    provider = manager.initialize("test-service", str(uuid.uuid4()))
    assert provider is not None
    
    # Get tracer
    tracer = manager.get_tracer("test-tracer")
    assert tracer is not None
    
    # Shutdown
    manager.shutdown()
    assert manager._tracer_provider is None
    assert len(manager._processors) == 0

# def test_exporter_retry():
#     """Test exporter retry mechanism"""
#     session_id = uuid.uuid4()
#     exporter = ExportManager(
#         session_id=session_id,
#         endpoint="http://invalid-host:8000/v2/create_events",  # Invalid endpoint to force retry
#         jwt="test-jwt",
#         api_key="test-key"
#     )
#     
#     # Create a test span (minimal attributes for testing)
#     @dataclass
#     class TestSpan:
#         name: str = "test"
#         attributes: dict = None
#     
#     span = TestSpan(attributes={
#         "event.data": "{}",
#         "event.id": str(uuid.uuid4()),
#         "event.timestamp": "2024-01-01T00:00:00Z",
#         "event.end_timestamp": "2024-01-01T00:00:01Z"
#     })
#     
#     # Export should fail but not raise exception
#     result = exporter.export([span])
#     assert result == exporter.SpanExportResult.FAILURE 
