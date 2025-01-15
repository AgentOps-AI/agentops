import json
import pytest
from opentelemetry.trace import SpanKind

from agentops.event import Event
from agentops.telemetry.encoders import EventToSpanEncoder, SpanDefinition


class TestEventToSpanEncoder:
    """Test the Event to Span conversion logic"""

    def test_llm_event_conversion(self, mock_llm_event):
        """Test converting LLMEvent to spans"""
        span_defs = EventToSpanEncoder.encode(mock_llm_event)

        # Verify we get exactly two spans for LLM events
        assert len(span_defs) == 2, f"Expected 2 spans for LLM event, got {len(span_defs)}"

        # Find the spans by name
        completion_span = next((s for s in span_defs if s.name == "llm.completion"), None)
        api_span = next((s for s in span_defs if s.name == "llm.api.call"), None)

        assert completion_span is not None, "Missing llm.completion span"
        assert api_span is not None, "Missing llm.api.call span"

        # Verify completion span attributes
        assert completion_span.attributes["model"] == mock_llm_event.model
        assert completion_span.attributes["prompt"] == mock_llm_event.prompt
        assert completion_span.attributes["completion"] == mock_llm_event.completion
        assert completion_span.attributes["prompt_tokens"] == 10
        assert completion_span.attributes["completion_tokens"] == 1
        assert completion_span.attributes["cost"] == 0.01
        assert completion_span.attributes["event.start_time"] == mock_llm_event.init_timestamp
        assert completion_span.attributes["event.end_time"] == mock_llm_event.end_timestamp

        # Verify API span attributes and relationships
        assert api_span.parent_span_id == completion_span.name
        assert api_span.kind == SpanKind.CLIENT
        assert api_span.attributes["model"] == mock_llm_event.model
        assert api_span.attributes["start_time"] == mock_llm_event.init_timestamp
        assert api_span.attributes["end_time"] == mock_llm_event.end_timestamp

    def test_action_event_conversion(self, mock_action_event):
        """Test converting ActionEvent to spans"""
        span_defs = EventToSpanEncoder.encode(mock_action_event)

        assert len(span_defs) == 2
        action_span = next((s for s in span_defs if s.name == "agent.action"), None)
        execution_span = next((s for s in span_defs if s.name == "action.execution"), None)

        assert action_span is not None
        assert execution_span is not None

        # Verify action span attributes
        assert action_span.attributes["action_type"] == "process_data"
        assert json.loads(action_span.attributes["params"]) == {"input_file": "data.csv"}
        assert action_span.attributes["returns"] == "100 rows processed"
        assert action_span.attributes["logs"] == "Successfully processed all rows"
        assert action_span.attributes["event.start_time"] == mock_action_event.init_timestamp

        # Verify execution span
        assert execution_span.parent_span_id == action_span.name
        assert execution_span.attributes["start_time"] == mock_action_event.init_timestamp
        assert execution_span.attributes["end_time"] == mock_action_event.end_timestamp

    def test_tool_event_conversion(self, mock_tool_event):
        """Test converting ToolEvent to spans"""
        span_defs = EventToSpanEncoder.encode(mock_tool_event)

        assert len(span_defs) == 2
        tool_span = next((s for s in span_defs if s.name == "agent.tool"), None)
        execution_span = next((s for s in span_defs if s.name == "tool.execution"), None)

        assert tool_span is not None
        assert execution_span is not None

        # Verify tool span attributes
        assert tool_span.attributes["name"] == "searchWeb"
        assert json.loads(tool_span.attributes["params"]) == {"query": "python testing"}
        assert json.loads(tool_span.attributes["returns"]) == ["result1", "result2"]
        assert json.loads(tool_span.attributes["logs"]) == {"status": "success"}

        # Verify execution span
        assert execution_span.parent_span_id == tool_span.name
        assert execution_span.attributes["start_time"] == mock_tool_event.init_timestamp
        assert execution_span.attributes["end_time"] == mock_tool_event.end_timestamp

    def test_error_event_conversion(self, mock_error_event):
        """Test converting ErrorEvent to spans"""
        span_defs = EventToSpanEncoder.encode(mock_error_event)

        assert len(span_defs) == 1
        error_span = span_defs[0]

        # Verify error span attributes
        assert error_span.name == "error"
        assert error_span.attributes["error"] is True
        assert error_span.attributes["error_type"] == "ValueError"
        assert error_span.attributes["details"] == "Detailed error info"
        assert "trigger_event" in error_span.attributes

    def test_unknown_event_type(self):
        """Test handling of unknown event types"""

        class UnknownEvent(Event):
            pass

        # Should still work, just with generic event name
        span_defs = EventToSpanEncoder.encode(UnknownEvent(event_type="unknown"))
        assert len(span_defs) == 1
        assert span_defs[0].name == "event"
