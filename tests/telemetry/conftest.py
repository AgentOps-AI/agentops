import time
import uuid
from dataclasses import dataclass
from typing import Dict, Any, Optional

import pytest
from opentelemetry.trace import SpanContext, TraceFlags


@dataclass
class TestSpan:
    """Test span implementation for testing, avoiding OpenTelemetry dependencies where possible"""
    name: str
    attributes: Dict[str, Any]
    context: Optional[SpanContext] = None
    parent_span_id: Optional[str] = None
    kind: Optional[str] = None
    _start_time: int = field(default_factory=lambda: time.time_ns())
    _end_time: Optional[int] = None

    def __post_init__(self):
        if self.context is None:
            # Create a deterministic span context for testing
            self.context = SpanContext(
                trace_id=uuid.uuid4().int & ((1 << 128) - 1),  # 128-bit trace id
                span_id=uuid.uuid4().int & ((1 << 64) - 1),    # 64-bit span id
                trace_flags=TraceFlags(TraceFlags.SAMPLED),
                is_remote=False,
            )

    def end(self, end_time: Optional[int] = None):
        """End the span with optional end time"""
        self._end_time = end_time or time.time_ns()

    def get_span_context(self):
        """Get span context - matches OpenTelemetry Span interface"""
        return self.context


@pytest.fixture
def test_span():
    """Create a basic test span"""
    def _create_span(name: str, attributes: Optional[Dict[str, Any]] = None) -> TestSpan:
        return TestSpan(name=name, attributes=attributes or {})
    return _create_span


@pytest.fixture
def mock_llm_event():
    """Creates an LLMEvent for testing"""
    from agentops.event import LLMEvent
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
    from agentops.event import ActionEvent
    return ActionEvent(
        action_type="process_data",
        params={"input_file": "data.csv"},
        returns="100 rows processed",
        logs="Successfully processed all rows",
    )


@pytest.fixture
def mock_tool_event():
    """Creates a ToolEvent for testing"""
    from agentops.event import ToolEvent
    return ToolEvent(
        name="searchWeb",
        params={"query": "python testing"},
        returns=["result1", "result2"],
        logs={"status": "success"},
    )


@pytest.fixture
def mock_error_event():
    """Creates an ErrorEvent for testing"""
    from agentops.event import ActionEvent, ErrorEvent
    trigger = ActionEvent(action_type="risky_action")
    error = ValueError("Something went wrong")
    return ErrorEvent(
        trigger_event=trigger,
        exception=error,
        error_type="ValueError",
        details="Detailed error info"
    )
