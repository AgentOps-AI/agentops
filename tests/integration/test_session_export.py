import time
from uuid import uuid4
from opentelemetry.sdk.trace import ReadableSpan, SpanExportResult
from agentops.session import Session, SessionExporter
from agentops.config import Configuration
from agentops.event import ActionEvent, LLMEvent

class TestExporter(SessionExporter):
    """Test exporter that tracks exports without making HTTP requests"""
    def __init__(self, session: Session, **kwargs):
        super().__init__(session, **kwargs)
        self.export_count = 0
        self.exported_spans = []
        
    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """Override export to count calls and store spans without making HTTP requests"""
        self.export_count += 1
        self.exported_spans.extend(spans)
        return SpanExportResult.SUCCESS

def test_session_export_behavior():
    """Test the export behavior of a session with multiple event types"""
    # Setup
    config = Configuration(
        api_key="test_key",
        max_queue_size=10,  # Small queue to force frequent exports
        max_wait_time=100   # Short delay (milliseconds) to speed up test
    )
    session = Session(session_id=uuid4(), config=config)
    
    # Replace real exporter with test exporter
    test_exporter = TestExporter(session=session)
    session._otel_exporter = test_exporter
    
    # Record different types of events
    # LLM events
    session.record(LLMEvent(
        prompt="What is 2+2?",
        completion="4",
        model="gpt-3.5-turbo"
    ))
    
    # Action events
    session.record(ActionEvent(
        action_type="calculate",
        params={"x": 2, "y": 2},
        returns="4"
    ))
    
    # Add some delay to allow for processing
    time.sleep(0.2)
    
    # Force flush to ensure all spans are exported
    session._span_processor.force_flush()
    
    # Verify exports occurred
    assert test_exporter.export_count > 0, "Export should have been called at least once"
    assert len(test_exporter.exported_spans) == 2, "Should have exported 2 spans"
    
    # Verify span contents
    spans_by_name = {span.name: span for span in test_exporter.exported_spans}
    
    # Check LLM span
    assert "llms" in spans_by_name, "Should have an LLM span"
    llm_span = spans_by_name["llms"]
    llm_data = llm_span.attributes.get("event.data")
    assert "gpt-3.5-turbo" in llm_data, "LLM span should contain model information"
    
    # Check Action span
    assert "actions" in spans_by_name, "Should have an Action span"
    action_span = spans_by_name["actions"]
    action_data = action_span.attributes.get("event.data")
    assert "calculate" in action_data, "Action span should contain action type"
    
    # Clean up
    session.end_session()
    
    print(f"Export was called {test_exporter.export_count} times")
    print(f"Total spans exported: {len(test_exporter.exported_spans)}")

def test_session_export_batching():
    """Test how the session batches events before exporting"""
    config = Configuration(
        api_key="test_key",
        max_queue_size=5,    # Small queue size
        max_wait_time=500    # Longer delay to test batching
    )
    session = Session(session_id=uuid4(), config=config)
    
    # Replace real exporter with test exporter
    test_exporter = TestExporter(session=session)
    session._otel_exporter = test_exporter
    
    # Record multiple events quickly
    for i in range(10):
        session.record(ActionEvent(
            action_type=f"test_action_{i}",
            params={"index": i}
        ))
    
    # Add delay to allow for processing
    time.sleep(1)
    
    # Force final flush
    session._span_processor.force_flush()
    
    # Verify batching behavior
    assert test_exporter.export_count >= 2, "Should have multiple export batches"
    assert len(test_exporter.exported_spans) == 10, "Should have exported all 10 spans"
    
    # Clean up
    session.end_session()
    
    print(f"Number of export batches: {test_exporter.export_count}")
    print(f"Average batch size: {len(test_exporter.exported_spans) / test_exporter.export_count:.1f}") 