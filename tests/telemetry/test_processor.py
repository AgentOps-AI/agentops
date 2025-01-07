import json
import time
import uuid
from contextlib import contextmanager
from unittest.mock import Mock, patch

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan, Span, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span, SpanContext, TraceFlags

from agentops.enums import EventType
from agentops.event import ActionEvent, ErrorEvent, Event, LLMEvent, ToolEvent
from agentops.telemetry.client import ClientTelemetry
from agentops.telemetry.manager import OTELManager
from agentops.telemetry.processors import EventProcessor, LiveSpanProcessor
from .test_event_converter import EventToSpanConverter, MockSpan

# Keep existing MockSpan class for backward compatibility
# but use the one from test_event_converter for new tests

@pytest.fixture
def mock_tracer():
    """
    Create a mock TracerProvider that returns a mock Tracer.
    Following the OpenTelemetry pattern where TracerProvider creates Tracers.
    """
    tracer = Mock(spec=trace.Tracer)

    @contextmanager
    def mock_span_context(name, attributes=None, **kwargs):
        span = MockSpan(name, attributes)
        yield span

    tracer.start_as_current_span = mock_span_context

    provider = Mock(spec=TracerProvider)
    provider.get_tracer = Mock(return_value=tracer)
    return provider


@pytest.fixture
def processor(mock_tracer):
    """Create an EventProcessor with a mock TracerProvider"""
    return EventProcessor(uuid.uuid4(), mock_tracer)


@pytest.fixture
def mock_span_exporter():
    return Mock()


@pytest.fixture
def mock_span():
    span = Mock(spec=Span)
    span.context = Mock(spec=SpanContext, span_id=123, trace_flags=TraceFlags(TraceFlags.SAMPLED))
    mock_readable = Mock(spec=ReadableSpan)
    mock_readable._attributes = {}
    mock_readable._start_time = time.time_ns()
    span._readable_span.return_value = mock_readable
    return span


@pytest.fixture
def live_processor(mock_span_exporter):
    return LiveSpanProcessor(mock_span_exporter)


class TestEventProcessor:
    def test_initialization(self, processor):
        """Test processor initialization"""
        expected_counts = {
            "llms": 0,
            "tools": 0,
            "actions": 0,
            "errors": 0,
            "apis": 0,
        }
        assert processor.event_counts == expected_counts, \
            f"Expected initial event counts {expected_counts}, got {processor.event_counts}"

    def test_process_action_event(self, processor):
        """Test processing an action event"""
        event = ActionEvent(
            action_type="test_action",
            params={"input": "test"},
            returns={"output": "success"},
            logs="Action completed successfully",
        )
        span = processor.process_event(event)

        assert span is not None, "Processor should return a span"
        assert processor.event_counts["actions"] == 1, \
            f"Expected actions count to be 1, got {processor.event_counts['actions']}"

        event_data = json.loads(span._attributes["event.data"])
        assert event_data["action_type"] == "test_action", \
            f"Expected action_type 'test_action', got '{event_data['action_type']}'"
        assert event_data["params"] == {"input": "test"}, \
            f"Expected params {{'input': 'test'}}, got {event_data['params']}"
        assert event_data["returns"] == {"output": "success"}, \
            f"Expected returns {{'output': 'success'}}, got {event_data['returns']}"
        assert event_data["logs"] == "Action completed successfully", \
            f"Expected logs 'Action completed successfully', got '{event_data['logs']}'"

    def test_process_llm_event(self, processor):
        """Test processing an LLM event"""
        event = LLMEvent(
            prompt="What is the meaning of life?",
            completion="42",
            model="gpt-4",
            prompt_tokens=10,
            completion_tokens=1,
            cost=0.01,
        )
        span = processor.process_event(event)

        assert span is not None, "Processor should return a span"
        assert processor.event_counts["llms"] == 1, \
            f"Expected llms count to be 1, got {processor.event_counts['llms']}"

        event_data = json.loads(span._attributes["event.data"])
        assert event_data["prompt"] == "What is the meaning of life?", \
            f"Expected prompt 'What is the meaning of life?', got '{event_data['prompt']}'"
        assert event_data["completion"] == "42", \
            f"Expected completion '42', got '{event_data['completion']}'"
        assert event_data["model"] == "gpt-4", \
            f"Expected model 'gpt-4', got '{event_data['model']}'"
        assert event_data["prompt_tokens"] == 10, \
            f"Expected prompt_tokens 10, got {event_data['prompt_tokens']}"
        assert event_data["completion_tokens"] == 1, \
            f"Expected completion_tokens 1, got {event_data['completion_tokens']}"
        assert event_data["cost"] == 0.01, \
            f"Expected cost 0.01, got {event_data['cost']}"

    def test_process_tool_event(self, processor):
        """Test processing a tool event"""
        event = ToolEvent(
            name="searchWeb",
            params={"query": "python testing"},
            returns={"results": ["result1", "result2"]},
            logs={"status": "success"},
        )
        span = processor.process_event(event)

        assert span is not None, "Processor should return a span"
        assert processor.event_counts["tools"] == 1, \
            f"Expected tools count to be 1, got {processor.event_counts['tools']}"

        event_data = json.loads(span._attributes["event.data"])
        assert event_data["name"] == "searchWeb", \
            f"Expected tool name 'searchWeb', got '{event_data['name']}'"
        assert event_data["params"]["query"] == "python testing", \
            f"Expected query 'python testing', got '{event_data['params']['query']}'"
        assert event_data["logs"]["status"] == "success", \
            f"Expected status 'success', got '{event_data['logs']['status']}'"

    def test_process_error_event(self, processor):
        """Test processing an error event"""
        # Create a trigger event
        trigger = ActionEvent(action_type="risky_action")

        # Create error event
        error = ValueError("Something went wrong")
        event = ErrorEvent(
            trigger_event=trigger,
            exception=error,
            error_type="ValueError",
            details="Detailed error info"
        )
        span = processor.process_event(event)

        assert span is not None, "Processor should return a span"
        assert processor.event_counts["errors"] == 1, \
            f"Expected errors count to be 1, got {processor.event_counts['errors']}"
        assert span._attributes["error"] is True, "Span should have error=True attribute"

        event_data = json.loads(span._attributes["event.data"])
        assert event_data["error_type"] == "ValueError", \
            f"Expected error_type 'ValueError', got '{event_data['error_type']}'"
        assert event_data["details"] == "Detailed error info", \
            f"Expected details 'Detailed error info', got '{event_data['details']}'"
        assert "trigger_event" in event_data, "Missing trigger_event in error data"

    def test_event_timestamps(self, processor):
        """Test event timestamp handling"""
        event = ActionEvent(action_type="test")
        span = processor.process_event(event)

        assert "event.timestamp" in span._attributes, "Missing event.timestamp attribute"
        assert "event.end_timestamp" in span._attributes, "Missing event.end_timestamp attribute"
        assert span._attributes["event.timestamp"] == event.init_timestamp, \
            f"Expected timestamp {event.init_timestamp}, got {span._attributes['event.timestamp']}"
        assert span._attributes["event.end_timestamp"] == event.end_timestamp, \
            f"Expected end timestamp {event.end_timestamp}, got {span._attributes['event.end_timestamp']}"

    def test_tags_handling(self, processor):
        """Test handling of event tags"""
        event = ActionEvent(action_type="test")
        tags = ["test", "smoke"]
        span = processor.process_event(event, tags=tags)

        assert span is not None, "Processor should return a span"
        assert span._attributes["session.tags"] == "test,smoke", \
            f"Expected tags 'test,smoke', got '{span._attributes['session.tags']}'"

    def test_agent_id_handling(self, processor):
        """Test handling of agent ID"""
        agent_id = uuid.uuid4()
        event = ActionEvent(action_type="test", agent_id=agent_id)
        span = processor.process_event(event)

        event_data = json.loads(span._attributes["event.data"])
        assert str(event_data["agent_id"]) == str(agent_id), \
            f"Expected agent_id {agent_id}, got {event_data['agent_id']}"

    def test_long_running_event(self, processor, live_processor, mock_span_exporter):
        """
        Test processing of long-running events with LiveSpanProcessor.

        This test demonstrates the proper OpenTelemetry pattern:
        1. Create a TracerProvider
        2. Register span processors with the provider
        3. Create spans through the provider's tracer
        4. Let the provider automatically handle span processing

        Instead of processors knowing about each other directly, they are
        coordinated through the TracerProvider, following OTEL's design.
        """
        # Create a mock tracer that will properly trigger span lifecycle events
        mock_span = MockSpan("llms")
        tracer = Mock(spec=trace.Tracer)

        @contextmanager
        def mock_span_context(name, attributes=None, **kwargs):
            mock_span._attributes = attributes or {}
            yield mock_span
            # Simulate span end by calling processor directly
            live_processor.on_start(mock_span)

        tracer.start_as_current_span = mock_span_context

        # Set up provider with our mock tracer
        provider = Mock(spec=TracerProvider)
        provider.get_tracer = Mock(return_value=tracer)
        provider.add_span_processor(live_processor)

        # Update the event processor to use our configured provider and tracer
        processor._tracer_provider = provider
        processor._tracer = tracer

        event = LLMEvent(
            prompt="Long running task",
            model="gpt-4",
        )

        # When this span is created, it will automatically be processed
        # by all processors registered with the provider
        span = processor.process_event(event)

        assert span is not None
        assert processor.event_counts["llms"] == 1
        # The span should be tracked by the live processor because it was
        # registered with the provider, not because of direct coupling
        assert span.context.span_id in live_processor._in_flight


class TestLiveSpanProcessor:
    def test_initialization(self, live_processor, mock_span_exporter):
        """Test processor initialization"""
        assert live_processor.span_exporter == mock_span_exporter, \
            "Span exporter not properly initialized"
        assert live_processor._in_flight == {}, \
            f"Expected empty in_flight dict, got {live_processor._in_flight}"
        assert not live_processor._stop_event.is_set(), \
            "Stop event should not be set on initialization"
        assert live_processor._export_thread.daemon, \
            "Export thread should be a daemon thread"
        assert live_processor._export_thread.is_alive(), \
            "Export thread should be running after initialization"

    def test_span_processing_lifecycle(self, live_processor, mock_span):
        """Test complete span lifecycle"""
        # Test span start
        live_processor.on_start(mock_span)
        assert mock_span.context.span_id in live_processor._in_flight, \
            f"Span ID {mock_span.context.span_id} not found in in_flight spans"

        # Test span end
        readable_span = Mock(spec=ReadableSpan)
        readable_span.context = mock_span.context
        live_processor.on_end(readable_span)

        assert mock_span.context.span_id not in live_processor._in_flight, \
            f"Span ID {mock_span.context.span_id} should be removed from in_flight spans"
        live_processor.span_exporter.export.assert_called_once_with((readable_span,)), \
            "Span exporter should be called exactly once with the readable span"

    def test_unsampled_span_ignored(self, live_processor):
        """Test that unsampled spans are ignored"""
        unsampled_span = Mock(spec=Span)
        unsampled_span.context = Mock(spec=SpanContext, trace_flags=TraceFlags(TraceFlags.DEFAULT))

        # Test span start
        live_processor.on_start(unsampled_span)
        assert len(live_processor._in_flight) == 0, \
            f"Unsampled span should not be added to in_flight, found {len(live_processor._in_flight)} spans"

        # Test span end
        live_processor.on_end(unsampled_span)
        live_processor.span_exporter.export.assert_not_called(), \
            "Span exporter should not be called for unsampled spans"

    @patch("time.sleep")
    def test_periodic_export(self, mock_sleep, live_processor, mock_span):
        """Test periodic export of in-flight spans"""
        live_processor.on_start(mock_span)

        with live_processor._lock:
            to_export = [live_processor._readable_span(span) for span in live_processor._in_flight.values()]
            if to_export:
                live_processor.span_exporter.export(to_export)

        exported_span = live_processor.span_exporter.export.call_args[0][0][0]
        assert exported_span._attributes["agentops.in_flight"] is True, \
            "Exported span should have agentops.in_flight=True"
        assert "agentops.duration_ms" in exported_span._attributes, \
            "Exported span should have agentops.duration_ms attribute"

    def test_concurrent_spans(self, live_processor):
        """Test handling multiple concurrent spans"""
        # Create test spans
        spans = [
            Mock(
                spec=Span,
                context=Mock(
                    spec=SpanContext,
                    span_id=i,
                    trace_flags=TraceFlags(TraceFlags.SAMPLED),
                ),
            )
            for i in range(3)
        ]

        # Start all spans
        for span in spans:
            live_processor.on_start(span)
        assert len(live_processor._in_flight) == 3, \
            f"Expected 3 in-flight spans, got {len(live_processor._in_flight)}"

        # End all spans
        for span in reversed(spans):
            readable_span = Mock(spec=ReadableSpan)
            readable_span.context = span.context
            live_processor.on_end(readable_span)
        assert len(live_processor._in_flight) == 0, \
            f"Expected 0 in-flight spans after completion, got {len(live_processor._in_flight)}"

    def test_shutdown(self, live_processor):
        """Test processor shutdown"""
        live_processor.shutdown()

        assert live_processor._stop_event.is_set(), \
            "Stop event should be set after shutdown"
        assert not live_processor._export_thread.is_alive(), \
            "Export thread should not be running after shutdown"
        live_processor.span_exporter.shutdown.assert_called_once(), \
            "Span exporter shutdown should be called exactly once"

    def test_readable_span_attributes(self, live_processor, mock_span):
        """Test attributes of readable spans"""
        readable = live_processor._readable_span(mock_span)

        assert "agentops.in_flight" in readable._attributes, \
            "Readable span should have agentops.in_flight attribute"
        assert readable._attributes["agentops.in_flight"] is True, \
            "agentops.in_flight should be True"
        assert "agentops.duration_ms" in readable._attributes, \
            "Readable span should have agentops.duration_ms attribute"
        assert isinstance(readable._end_time, int), \
            f"End time should be an integer, got {type(readable._end_time)}"


class TestOTELIntegration:
    """Test integration between OTELManager, processors, and client telemetry"""

    @pytest.fixture
    def mock_config(self):
        config = Mock()
        config.max_queue_size = 1000
        config.max_wait_time = 5000
        return config

    def test_manager_processor_integration(self, mock_config, mock_span_exporter):
        """Test OTELManager with both BatchSpanProcessor and LiveSpanProcessor"""
        manager = OTELManager(mock_config)

        # Initialize manager
        provider = manager.initialize("test_service", "test_session")
        assert provider is not None

        # Add both types of processors
        batch_processor = BatchSpanProcessor(mock_span_exporter)
        live_processor = LiveSpanProcessor(mock_span_exporter)

        manager.add_processor(batch_processor)
        manager.add_processor(live_processor)

        # Verify both processors are added
        assert len(manager._processors) == 2
        assert any(isinstance(p, BatchSpanProcessor) for p in manager._processors)
        assert any(isinstance(p, LiveSpanProcessor) for p in manager._processors)

        # Create a span and verify it's processed by both processors
        tracer = manager.get_tracer("test")
        with tracer.start_as_current_span("test_span") as span:
            assert span is not None
            # Verify span is in live processor's in_flight
            assert span.context.span_id in live_processor._in_flight

        # Cleanup
        manager.shutdown()
        assert len(manager._processors) == 0

    def test_client_telemetry_integration(self, mock_config):
        """Test full integration with ClientTelemetry"""
        client = ClientTelemetry()
        client.initialize(mock_config)

        session_id = uuid.uuid4()
        jwt = "test_jwt"

        # Get session tracer
        tracer = client.get_session_tracer(session_id, mock_config, jwt)
        assert tracer is not None

        # Create a span
        with tracer.start_as_current_span("test_operation") as span:
            assert span is not None

        # Cleanup
        client.cleanup_session(session_id)
        client.shutdown()
