import json
import pytest

from agentops.event import Event
from agentops.telemetry.converter import EventToSpanConverter, SpanDefinition

class TestEventToSpanConverter:
    """Test the Event to Span conversion logic"""

    def test_llm_event_conversion(self, mock_llm_event):
        """Test converting LLMEvent to spans"""
        span_defs = EventToSpanConverter.convert_event(mock_llm_event)

        # Verify we get exactly two spans for LLM events
        assert len(span_defs) == 2, f"Expected 2 spans for LLM event, got {len(span_defs)}"

        # Find the spans by name
        completion_span = next((s for s in span_defs if s.name == "llm.completion"), None)
        api_span = next((s for s in span_defs if s.name == "llm.api.call"), None)

        assert completion_span is not None, "Missing llm.completion span"
        assert api_span is not None, "Missing llm.api.call span"

        # Verify completion span attributes
        assert completion_span.attributes["llm.model"] == mock_llm_event.model
        assert completion_span.attributes["llm.prompt"] == mock_llm_event.prompt
        assert completion_span.attributes["llm.completion"] == mock_llm_event.completion
        assert completion_span.attributes["llm.tokens.total"] == 11  # 10 prompt + 1 completion
        assert completion_span.attributes["llm.cost"] == 0.01

        # Verify API span attributes and relationships
        assert api_span.parent_span_id == completion_span.name
        assert api_span.kind == "client"
        assert api_span.attributes["llm.model"] == mock_llm_event.model
        assert "llm.request.timestamp" in api_span.attributes
        assert "llm.response.timestamp" in api_span.attributes

    def test_action_event_conversion(self, mock_action_event):
        """Test converting ActionEvent to spans"""
        span_defs = EventToSpanConverter.convert_event(mock_action_event)

        assert len(span_defs) == 2
        action_span = next((s for s in span_defs if s.name == "agent.action"), None)
        execution_span = next((s for s in span_defs if s.name == "action.execution"), None)

        assert action_span is not None
        assert execution_span is not None

        # Verify action span attributes
        assert action_span.attributes["action.type"] == "process_data"
        assert json.loads(action_span.attributes["action.params"]) == {"input_file": "data.csv"}
        assert action_span.attributes["action.logs"] == "Successfully processed all rows"

        # Verify execution span
        assert execution_span.parent_span_id == action_span.name
        assert "execution.start_time" in execution_span.attributes
        assert "execution.end_time" in execution_span.attributes

    def test_tool_event_conversion(self, mock_tool_event):
        """Test converting ToolEvent to spans"""
        span_defs = EventToSpanConverter.convert_event(mock_tool_event)

        assert len(span_defs) == 2
        tool_span = next((s for s in span_defs if s.name == "agent.tool"), None)
        execution_span = next((s for s in span_defs if s.name == "tool.execution"), None)

        assert tool_span is not None
        assert execution_span is not None

        # Verify tool span attributes
        assert tool_span.attributes["tool.name"] == "searchWeb"
        assert json.loads(tool_span.attributes["tool.params"]) == {"query": "python testing"}
        assert json.loads(tool_span.attributes["tool.result"]) == ["result1", "result2"]
        assert json.loads(tool_span.attributes["tool.logs"]) == {"status": "success"}

        # Verify execution span
        assert execution_span.parent_span_id == tool_span.name
        assert "execution.start_time" in execution_span.attributes
        assert "execution.end_time" in execution_span.attributes

    def test_error_event_conversion(self, mock_error_event):
        """Test converting ErrorEvent to spans"""
        span_defs = EventToSpanConverter.convert_event(mock_error_event)

        assert len(span_defs) == 1
        error_span = span_defs[0]

        # Verify error span attributes
        assert error_span.name == "error"
        assert error_span.attributes["error"] is True
        assert error_span.attributes["error.type"] == "ValueError"
        assert error_span.attributes["error.details"] == "Detailed error info"

        # Verify trigger event data
        trigger_data = json.loads(error_span.attributes["error.trigger_event"])
        assert trigger_data["type"] == "action"
        assert trigger_data["action_type"] == "risky_action"

    def test_unknown_event_type(self):
        """Test handling of unknown event types"""
        class UnknownEvent(Event):
            pass

        with pytest.raises(ValueError, match="No converter found for event type"):
            EventToSpanConverter.convert_event(UnknownEvent(event_type="unknown"))
