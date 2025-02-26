import unittest
from unittest.mock import MagicMock, patch

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.semconv_ai import SpanAttributes, LLMRequestTypeValues

from agentops.telemetry.span_processor import MetricsSpanProcessor


class TestMetricsSpanProcessor(unittest.TestCase):
    """Test the MetricsSpanProcessor class."""
    
    def setUp(self):
        """Set up the test."""
        # Mock the exporter
        self.exporter = MagicMock()
        
        # Create a metrics span processor
        self.processor = MetricsSpanProcessor(self.exporter, "test-session-id")
        
        # Mock the counters
        self.processor.llm_counter = MagicMock()
        self.processor.tool_counter = MagicMock()
        self.processor.action_counter = MagicMock()
        self.processor.error_counter = MagicMock()
        self.processor.api_counter = MagicMock()
    
    def test_process_span_llm_chat(self):
        """Test processing an LLM chat span."""
        # Create a mock span with LLM chat attributes
        span = MagicMock(spec=ReadableSpan)
        span.attributes = {
            SpanAttributes.LLM_REQUEST_TYPE: LLMRequestTypeValues.CHAT.value
        }
        span.status.is_error = False
        
        # Process the span
        self.processor._process_span(span)
        
        # Verify that the LLM counter was incremented
        self.processor.llm_counter.add.assert_called_once_with(1, {"session_id": "test-session-id"})
        self.assertEqual(self.processor.event_counts["llms"], 1)
        
        # Verify that other counters were not incremented
        self.processor.tool_counter.add.assert_not_called()
        self.processor.action_counter.add.assert_not_called()
        self.processor.error_counter.add.assert_not_called()
        self.processor.api_counter.add.assert_not_called()
    
    def test_process_span_llm_completion(self):
        """Test processing an LLM completion span."""
        # Create a mock span with LLM completion attributes
        span = MagicMock(spec=ReadableSpan)
        span.attributes = {
            SpanAttributes.LLM_REQUEST_TYPE: LLMRequestTypeValues.COMPLETION.value
        }
        span.status.is_error = False
        
        # Process the span
        self.processor._process_span(span)
        
        # Verify that the LLM counter was incremented
        self.processor.llm_counter.add.assert_called_once_with(1, {"session_id": "test-session-id"})
        self.assertEqual(self.processor.event_counts["llms"], 1)
        
        # Verify that other counters were not incremented
        self.processor.tool_counter.add.assert_not_called()
        self.processor.action_counter.add.assert_not_called()
        self.processor.error_counter.add.assert_not_called()
        self.processor.api_counter.add.assert_not_called()
    
    def test_process_span_embedding(self):
        """Test processing an embedding span."""
        # Create a mock span with embedding attributes
        span = MagicMock(spec=ReadableSpan)
        span.attributes = {
            SpanAttributes.LLM_REQUEST_TYPE: LLMRequestTypeValues.EMBEDDING.value
        }
        span.status.is_error = False
        
        # Process the span
        self.processor._process_span(span)
        
        # Verify that the API counter was incremented
        self.processor.api_counter.add.assert_called_once_with(1, {"session_id": "test-session-id"})
        self.assertEqual(self.processor.event_counts["apis"], 1)
        
        # Verify that other counters were not incremented
        self.processor.llm_counter.add.assert_not_called()
        self.processor.tool_counter.add.assert_not_called()
        self.processor.action_counter.add.assert_not_called()
        self.processor.error_counter.add.assert_not_called()
    
    def test_process_span_tool(self):
        """Test processing a tool span."""
        # Create a mock span with tool attributes
        span = MagicMock(spec=ReadableSpan)
        span.attributes = {
            "span.kind": "tool"
        }
        span.status.is_error = False
        
        # Process the span
        self.processor._process_span(span)
        
        # Verify that the tool counter was incremented
        self.processor.tool_counter.add.assert_called_once_with(1, {"session_id": "test-session-id"})
        self.assertEqual(self.processor.event_counts["tools"], 1)
        
        # Verify that other counters were not incremented
        self.processor.llm_counter.add.assert_not_called()
        self.processor.action_counter.add.assert_not_called()
        self.processor.error_counter.add.assert_not_called()
        self.processor.api_counter.add.assert_not_called()
    
    def test_process_span_action(self):
        """Test processing an action span."""
        # Create a mock span with action attributes
        span = MagicMock(spec=ReadableSpan)
        span.attributes = {
            "span.kind": "action"
        }
        span.status.is_error = False
        
        # Process the span
        self.processor._process_span(span)
        
        # Verify that the action counter was incremented
        self.processor.action_counter.add.assert_called_once_with(1, {"session_id": "test-session-id"})
        self.assertEqual(self.processor.event_counts["actions"], 1)
        
        # Verify that other counters were not incremented
        self.processor.llm_counter.add.assert_not_called()
        self.processor.tool_counter.add.assert_not_called()
        self.processor.error_counter.add.assert_not_called()
        self.processor.api_counter.add.assert_not_called()
    
    def test_process_span_api(self):
        """Test processing an API span."""
        # Create a mock span with API attributes
        span = MagicMock(spec=ReadableSpan)
        span.attributes = {
            "span.kind": "api"
        }
        span.status.is_error = False
        
        # Process the span
        self.processor._process_span(span)
        
        # Verify that the API counter was incremented
        self.processor.api_counter.add.assert_called_once_with(1, {"session_id": "test-session-id"})
        self.assertEqual(self.processor.event_counts["apis"], 1)
        
        # Verify that other counters were not incremented
        self.processor.llm_counter.add.assert_not_called()
        self.processor.tool_counter.add.assert_not_called()
        self.processor.action_counter.add.assert_not_called()
        self.processor.error_counter.add.assert_not_called()
    
    def test_process_span_error(self):
        """Test processing an error span."""
        # Create a mock span with error status
        span = MagicMock(spec=ReadableSpan)
        span.attributes = {}
        span.status.is_error = True
        
        # Process the span
        self.processor._process_span(span)
        
        # Verify that the error counter was incremented
        self.processor.error_counter.add.assert_called_once_with(1, {"session_id": "test-session-id"})
        self.assertEqual(self.processor.event_counts["errors"], 1)
        
        # Verify that other counters were not incremented
        self.processor.llm_counter.add.assert_not_called()
        self.processor.tool_counter.add.assert_not_called()
        self.processor.action_counter.add.assert_not_called()
        self.processor.api_counter.add.assert_not_called()
    
    def test_process_span_unknown(self):
        """Test processing a span with unknown attributes."""
        # Create a mock span with unknown attributes
        span = MagicMock(spec=ReadableSpan)
        span.attributes = {
            "unknown.attribute": "unknown.value"
        }
        span.status.is_error = False
        
        # Process the span
        self.processor._process_span(span)
        
        # Verify that no counters were incremented
        self.processor.llm_counter.add.assert_not_called()
        self.processor.tool_counter.add.assert_not_called()
        self.processor.action_counter.add.assert_not_called()
        self.processor.error_counter.add.assert_not_called()
        self.processor.api_counter.add.assert_not_called()
    
    def test_on_end(self):
        """Test the on_end method."""
        # Create a mock span
        span = MagicMock(spec=ReadableSpan)
        span.attributes = {
            SpanAttributes.LLM_REQUEST_TYPE: LLMRequestTypeValues.CHAT.value
        }
        span.status.is_error = False
        
        # Mock the _process_span method
        self.processor._process_span = MagicMock()
        
        # Call on_end
        self.processor.on_end(span)
        
        # Verify that _process_span was called with the span
        self.processor._process_span.assert_called_once_with(span)
        
        # Verify that super().on_end was called
        # This is difficult to test directly, so we'll skip it for now


if __name__ == "__main__":
    unittest.main()
