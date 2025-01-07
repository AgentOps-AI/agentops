import json
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from unittest.mock import Mock

import pytest
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.trace import SpanContext, TraceFlags

from agentops.event import ActionEvent, ErrorEvent, Event, LLMEvent, ToolEvent


@dataclass
class SpanDefinition:
    """Defines how a span should be created"""

    name: str
    attributes: Dict[str, Any]
    parent_span_id: Optional[str] = None
    kind: Optional[str] = None


class MockSpan:
    """Mock span for testing"""

    def __init__(self, name: str, attributes: dict = None):
        self.name = name
        self._attributes = attributes or {}
        self.context = Mock(
            spec=SpanContext,
            span_id=uuid.uuid4().int & ((1 << 64) - 1),
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
            trace_id=uuid.uuid4().int & ((1 << 128) - 1),
        )
        self.parent_span_id = None
        self._start_time = time.time_ns()
        self._end_time = None
        self.status = None
        self.kind = None

    def _readable_span(self):
        mock_readable = Mock(spec=ReadableSpan)
        mock_readable._attributes = self._attributes
        mock_readable._start_time = self._start_time
        mock_readable._end_time = self._end_time or time.time_ns()
        mock_readable.status = self.status
        mock_readable.name = self.name
        mock_readable.context = self.context
        mock_readable.parent_span_id = self.parent_span_id
        mock_readable.kind = self.kind
        return mock_readable


@pytest.fixture
def mock_llm_event():
    """Creates an LLMEvent for testing"""
    return LLMEvent(
        prompt="What is the meaning of life?",
        completion="42",
        model="gpt-4",
        prompt_tokens=10,
        completion_tokens=1,
        cost=0.01,
    )


@pytest.fixture
def mock_action_event():
    """Creates an ActionEvent for testing"""
    return ActionEvent(
        action_type="process_data",
        params={"input_file": "data.csv"},
        returns={"rows_processed": 100},
        logs="Successfully processed all rows",
    )


@pytest.fixture
def mock_tool_event():
    """Creates a ToolEvent for testing"""
    return ToolEvent(
        name="searchWeb",
        params={"query": "python testing"},
        returns={"results": ["result1", "result2"]},
        logs={"status": "success"},
    )


@pytest.fixture
def mock_error_event():
    """Creates an ErrorEvent for testing"""
    trigger = ActionEvent(action_type="risky_action")
    error = ValueError("Something went wrong")
    return ErrorEvent(trigger_event=trigger, exception=error, error_type="ValueError", details="Detailed error info")


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
        assert (
            completion_span.attributes["llm.model"] == mock_llm_event.model
        ), f"Expected model {mock_llm_event.model}, got {completion_span.attributes['llm.model']}"

        expected_tokens = mock_llm_event.prompt_tokens + mock_llm_event.completion_tokens
        assert (
            completion_span.attributes["llm.tokens.total"] == expected_tokens
        ), f"Expected {expected_tokens} total tokens, got {completion_span.attributes['llm.tokens.total']}"

        assert (
            completion_span.attributes["llm.cost"] == mock_llm_event.cost
        ), f"Expected cost {mock_llm_event.cost}, got {completion_span.attributes['llm.cost']}"

        assert (
            completion_span.attributes["llm.prompt"] == mock_llm_event.prompt
        ), f"Expected prompt '{mock_llm_event.prompt}', got '{completion_span.attributes['llm.prompt']}'"

        assert (
            completion_span.attributes["llm.completion"] == mock_llm_event.completion
        ), f"Expected completion '{mock_llm_event.completion}', got '{completion_span.attributes['llm.completion']}'"

        # Verify API span attributes and relationships
        assert (
            api_span.parent_span_id == completion_span.name
        ), f"API span should have parent ID {completion_span.name}, got {api_span.parent_span_id}"

        assert "llm.request.timestamp" in api_span.attributes, "API span missing llm.request.timestamp attribute"
        assert "llm.response.timestamp" in api_span.attributes, "API span missing llm.response.timestamp attribute"

    def test_action_event_conversion(self, mock_action_event):
        """Test converting ActionEvent to spans"""
        span_defs = EventToSpanConverter.convert_event(mock_action_event)

        # Verify we get exactly two spans for Action events
        assert len(span_defs) == 2, f"Expected 2 spans for Action event, got {len(span_defs)}"

        # Find the spans by name
        action_span = next((s for s in span_defs if s.name == "agent.action"), None)
        execution_span = next((s for s in span_defs if s.name == "action.execution"), None)

        assert action_span is not None, "Missing agent.action span"
        assert execution_span is not None, "Missing action.execution span"

        # Verify action span attributes
        assert (
            action_span.attributes["action.type"] == mock_action_event.action_type
        ), f"Expected action type '{mock_action_event.action_type}', got '{action_span.attributes['action.type']}'"

        expected_params = mock_action_event.params
        actual_params = json.loads(action_span.attributes["action.params"])
        assert actual_params == expected_params, f"Expected params {expected_params}, got {actual_params}"

        expected_returns = mock_action_event.returns
        actual_returns = json.loads(action_span.attributes["action.result"])
        assert actual_returns == expected_returns, f"Expected returns {expected_returns}, got {actual_returns}"

        assert (
            action_span.attributes["action.logs"] == mock_action_event.logs
        ), f"Expected logs '{mock_action_event.logs}', got '{action_span.attributes['action.logs']}'"

        # Verify execution span attributes and relationships
        assert (
            execution_span.parent_span_id == action_span.name
        ), f"Execution span should have parent ID {action_span.name}, got {execution_span.parent_span_id}"

        assert (
            execution_span.attributes["execution.start_time"] == mock_action_event.init_timestamp
        ), f"Expected start time {mock_action_event.init_timestamp}, got {execution_span.attributes['execution.start_time']}"

        assert (
            execution_span.attributes["execution.end_time"] == mock_action_event.end_timestamp
        ), f"Expected end time {mock_action_event.end_timestamp}, got {execution_span.attributes['execution.end_time']}"

    def test_tool_event_conversion(self, mock_tool_event):
        """Test converting ToolEvent to spans"""
        span_defs = EventToSpanConverter.convert_event(mock_tool_event)

        # Verify we get exactly two spans for Tool events
        assert len(span_defs) == 2, f"Expected 2 spans for Tool event, got {len(span_defs)}"

        # Find the spans by name
        tool_span = next((s for s in span_defs if s.name == "agent.tool"), None)
        execution_span = next((s for s in span_defs if s.name == "tool.execution"), None)

        assert tool_span is not None, "Missing agent.tool span"
        assert execution_span is not None, "Missing tool.execution span"

        # Verify tool span attributes
        assert (
            tool_span.attributes["tool.name"] == mock_tool_event.name
        ), f"Expected tool name '{mock_tool_event.name}', got '{tool_span.attributes['tool.name']}'"

        expected_params = mock_tool_event.params
        actual_params = json.loads(tool_span.attributes["tool.params"])
        assert actual_params == expected_params, f"Expected params {expected_params}, got {actual_params}"

        expected_returns = mock_tool_event.returns
        actual_returns = json.loads(tool_span.attributes["tool.result"])
        assert actual_returns == expected_returns, f"Expected returns {expected_returns}, got {actual_returns}"

        expected_logs = mock_tool_event.logs
        actual_logs = json.loads(tool_span.attributes["tool.logs"])
        assert actual_logs == expected_logs, f"Expected logs {expected_logs}, got {actual_logs}"

        # Verify execution span attributes and relationships
        assert (
            execution_span.parent_span_id == tool_span.name
        ), f"Execution span should have parent ID {tool_span.name}, got {execution_span.parent_span_id}"

        assert (
            execution_span.attributes["execution.start_time"] == mock_tool_event.init_timestamp
        ), f"Expected start time {mock_tool_event.init_timestamp}, got {execution_span.attributes['execution.start_time']}"

        assert (
            execution_span.attributes["execution.end_time"] == mock_tool_event.end_timestamp
        ), f"Expected end time {mock_tool_event.end_timestamp}, got {execution_span.attributes['execution.end_time']}"

    def test_error_event_conversion(self, mock_error_event):
        """Test converting ErrorEvent to spans"""
        span_defs = EventToSpanConverter.convert_event(mock_error_event)

        # Verify we get exactly one span for Error events
        assert len(span_defs) == 1, f"Expected 1 span for Error event, got {len(span_defs)}"
        error_span = span_defs[0]

        # Verify error span attributes
        assert error_span.name == "error", f"Expected span name 'error', got '{error_span.name}'"
        assert error_span.attributes["error"] is True, "Error span should have error=True"

        assert (
            error_span.attributes["error.type"] == mock_error_event.error_type
        ), f"Expected error type '{mock_error_event.error_type}', got '{error_span.attributes['error.type']}'"

        assert (
            error_span.attributes["error.details"] == mock_error_event.details
        ), f"Expected error details '{mock_error_event.details}', got '{error_span.attributes['error.details']}'"

        # Verify trigger event data
        trigger_event = json.loads(error_span.attributes["error.trigger_event"])
        assert trigger_event["type"] == "action", f"Expected trigger event type 'action', got '{trigger_event['type']}'"

        assert (
            trigger_event["action_type"] == mock_error_event.trigger_event.action_type
        ), f"Expected trigger action type '{mock_error_event.trigger_event.action_type}', got '{trigger_event['action_type']}'"

    def test_unknown_event_type(self):
        """Test handling of unknown event types"""

        class UnknownEvent(Event):
            pass

        with pytest.raises(ValueError, match="No converter found for event type") as exc_info:
            EventToSpanConverter.convert_event(UnknownEvent(event_type="unknown"))

        assert str(exc_info.value).startswith(
            "No converter found for event type"
        ), f"Expected error message about unknown event type, got: {str(exc_info.value)}"
