import json

import pytest
from opentelemetry.trace import SpanKind

from agentops.event import Event
from agentops.session.encoders import EventToSpanEncoder, SpanDefinition

# pytestmark = [pytest.mark.skip]


class TestEventToSpanEncoder:
    """Test the Event to Span conversion logic"""

    def test_llm_event_conversion(self, mock_llm_event):
        """Test converting LLMEvent to spans"""
        span_defs = EventToSpanEncoder.encode(mock_llm_event)

        assert len(span_defs) == 1
        completion_span = span_defs[0]

        assert completion_span.name == "llm.completion"

        # Verify completion span attributes
        assert completion_span.attributes["model"] == mock_llm_event.model
        assert completion_span.attributes["prompt"] == mock_llm_event.prompt
        assert completion_span.attributes["completion"] == mock_llm_event.completion
        assert completion_span.attributes["prompt_tokens"] == 10
        assert completion_span.attributes["completion_tokens"] == 1
        assert completion_span.attributes["cost"] == 0.01
        assert completion_span.attributes["event.start_time"] == mock_llm_event.init_timestamp
        # assert completion_span.attributes["event.end_timestamp"] == mock_llm_event.end_timestamp

    def test_action_event_conversion(self, mock_action_event):
        """Test converting ActionEvent to spans"""
        span_defs = EventToSpanEncoder.encode(mock_action_event)

        assert len(span_defs) == 1
        action_span = span_defs[0]

        assert action_span.name == "agent.action"

        # Verify action span attributes
        assert action_span.attributes["action_type"] == "process_data"
        assert json.loads(action_span.attributes["params"]) == {"input_file": "data.csv"}
        assert action_span.attributes["returns"] == "100 rows processed"
        assert action_span.attributes["logs"] == "Successfully processed all rows"
        assert action_span.attributes["event.start_time"] == mock_action_event.init_timestamp

    def test_tool_event_conversion(self, mock_tool_event):
        """Test converting ToolEvent to spans"""
        span_defs = EventToSpanEncoder.encode(mock_tool_event)

        assert len(span_defs) == 1
        tool_span = span_defs[0]

        assert tool_span.name == "agent.tool"

        # Verify tool span attributes
        assert tool_span.attributes["name"] == "searchWeb"
        assert json.loads(tool_span.attributes["params"]) == {"query": "python testing"}
        assert json.loads(tool_span.attributes["returns"]) == ["result1", "result2"]
        assert json.loads(tool_span.attributes["logs"]) == {"status": "success"}

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
