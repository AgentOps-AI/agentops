import pytest
from unittest.mock import patch, MagicMock, ANY

from opentelemetry import trace
from opentelemetry.trace import Span, SpanContext, TraceFlags

from agentops.sdk.decorators.session import session
from agentops.sdk.decorators.agent import agent
from agentops.sdk.decorators.tool import tool
from agentops.sdk.spans.session import SessionSpan
from agentops.sdk.spans.agent import AgentSpan
from agentops.sdk.spans.tool import ToolSpan


# Session Decorator Tests
@patch("agentops.sdk.decorators.session.TracingCore")
def test_session_class_decoration(mock_tracing_core):
    """Test decorating a class with session."""
    # Setup mock
    mock_span = MagicMock(spec=SessionSpan)
    mock_span.span = MagicMock(spec=Span)
    mock_instance = mock_tracing_core.get_instance.return_value
    mock_instance.create_span.return_value = mock_span

    # Create a decorated class
    @session(name="test_session", tags=["tag1", "tag2"])
    class TestClass:
        def __init__(self, arg1, arg2=None):
            self.arg1 = arg1
            self.arg2 = arg2

        def method(self):
            return f"{self.arg1}:{self.arg2}"

    # Instantiate and test
    test = TestClass("test1", "test2")
    assert test.arg1 == "test1"
    assert test.arg2 == "test2"
    assert test._session_span == mock_span

    # Verify that TracingCore was called correctly
    mock_instance.create_span.assert_called_once_with(
        kind="session", name="test_session", attributes={}, immediate_export=True, config=ANY, tags=["tag1", "tag2"]
    )

    # Verify the span was started
    mock_span.start.assert_called_once()


@patch("agentops.sdk.decorators.session.TracingCore")
def test_session_function_decoration(mock_tracing_core):
    """Test decorating a function with session."""
    # Setup mock
    mock_span = MagicMock(spec=SessionSpan)
    mock_span.span = MagicMock(spec=Span)
    mock_instance = mock_tracing_core.get_instance.return_value
    mock_instance.create_span.return_value = mock_span

    # Create a decorated function
    @session(name="test_session", tags=["tag1", "tag2"])
    def test_function(arg1, arg2=None):
        current_span = trace.get_current_span()
        return f"{arg1}:{arg2}:{current_span}"

    # Mock trace.get_current_span to return our mock span
    with patch("opentelemetry.trace.get_current_span", return_value=mock_span.span):
        # Call and test
        result = test_function("test1", "test2")

    # Verify that TracingCore was called correctly
    mock_instance.create_span.assert_called_once_with(
        kind="session", name="test_session", attributes={}, immediate_export=True, config=ANY, tags=["tag1", "tag2"]
    )

    # Verify the span was started and ended
    mock_span.start.assert_called_once()
    mock_span.end.assert_called_once_with("SUCCEEDED")

    # Result should include the mock_span
    assert "test1:test2:" in result
    assert str(mock_span.span) in result


# Agent Decorator Tests
@patch("agentops.sdk.decorators.agent.trace.get_current_span")
@patch("agentops.sdk.decorators.agent.TracingCore")
def test_agent_class_decoration(mock_tracing_core, mock_get_current_span):
    """Test decorating a class with agent."""
    # Setup mocks
    mock_parent_span = MagicMock(spec=Span)
    mock_parent_span.is_recording.return_value = True
    mock_parent_context = SpanContext(
        trace_id=0x12345678901234567890123456789012,
        span_id=0x1234567890123456,
        trace_flags=TraceFlags(TraceFlags.SAMPLED),
        is_remote=False,
    )
    mock_parent_span.get_span_context.return_value = mock_parent_context
    mock_get_current_span.return_value = mock_parent_span

    mock_agent_span = MagicMock(spec=AgentSpan)
    mock_agent_span.span = MagicMock(spec=Span)
    mock_instance = mock_tracing_core.get_instance.return_value
    mock_instance.create_span.return_value = mock_agent_span

    # Create a decorated class
    @agent(name="test_agent", agent_type="assistant")
    class TestAgent:
        def __init__(self, arg1, arg2=None):
            self.arg1 = arg1
            self.arg2 = arg2

        def method(self):
            return f"{self.arg1}:{self.arg2}"

    # Instantiate and test
    test = TestAgent("test1", "test2")
    assert test.arg1 == "test1"
    assert test.arg2 == "test2"
    assert test._agent_span == mock_agent_span

    # Verify that trace.get_current_span was called
    mock_get_current_span.assert_called()

    # Verify that TracingCore was called correctly
    mock_instance.create_span.assert_called_once_with(
        kind="agent",
        name="test_agent",
        parent=mock_parent_span,
        attributes={},
        immediate_export=True,
        agent_type="assistant",
    )

    # Verify the span was started
    mock_agent_span.start.assert_called_once()

    # Test a method call
    result = test.method()
    assert result == "test1:test2"


@patch("agentops.sdk.decorators.agent.trace.get_current_span")
@patch("agentops.sdk.decorators.agent.TracingCore")
def test_agent_function_decoration(mock_tracing_core, mock_get_current_span):
    """Test decorating a function with agent."""
    # Setup mocks
    mock_parent_span = MagicMock(spec=Span)
    mock_parent_span.is_recording.return_value = True
    mock_parent_context = SpanContext(
        trace_id=0x12345678901234567890123456789012,
        span_id=0x1234567890123456,
        trace_flags=TraceFlags(TraceFlags.SAMPLED),
        is_remote=False,
    )
    mock_parent_span.get_span_context.return_value = mock_parent_context
    mock_get_current_span.return_value = mock_parent_span

    mock_agent_span = MagicMock(spec=AgentSpan)
    mock_agent_span.span = MagicMock(spec=Span)
    mock_instance = mock_tracing_core.get_instance.return_value
    mock_instance.create_span.return_value = mock_agent_span

    # Create a decorated function that uses trace.get_current_span()
    @agent(name="test_agent", agent_type="assistant")
    def test_function(arg1, arg2=None):
        current_span = trace.get_current_span()
        return f"{arg1}:{arg2}:{current_span}"

    # Mock trace.get_current_span inside the function to return our agent span
    with patch("opentelemetry.trace.get_current_span", side_effect=[mock_parent_span, mock_agent_span.span]):
        # Call and test
        result = test_function("test1", "test2")

    # Verify that TracingCore was called correctly
    mock_instance.create_span.assert_called_once_with(
        kind="agent",
        name="test_agent",
        parent=mock_parent_span,
        attributes={},
        immediate_export=True,
        agent_type="assistant",
    )

    # Verify the span was started
    mock_agent_span.start.assert_called_once()

    # Result should include the mock_span
    assert "test1:test2:" in result
    assert str(mock_agent_span.span) in result

    # Test when no parent span is found
    mock_get_current_span.return_value = None
    result = test_function("test1", "test2")
    assert result == "test1:test2:None"


# Tool Decorator Tests
@patch("agentops.sdk.decorators.tool.trace.get_current_span")
@patch("agentops.sdk.decorators.tool.TracingCore")
def test_tool_function_decoration(mock_tracing_core, mock_get_current_span):
    """Test decorating a function with tool."""
    # Setup mocks
    mock_parent_span = MagicMock(spec=Span)
    mock_parent_span.is_recording.return_value = True
    mock_parent_context = SpanContext(
        trace_id=0x12345678901234567890123456789012,
        span_id=0x1234567890123456,
        trace_flags=TraceFlags(TraceFlags.SAMPLED),
        is_remote=False,
    )
    mock_parent_span.get_span_context.return_value = mock_parent_context
    mock_get_current_span.return_value = mock_parent_span

    mock_tool_span = MagicMock(spec=ToolSpan)
    mock_tool_span.span = MagicMock(spec=Span)
    mock_instance = mock_tracing_core.get_instance.return_value
    mock_instance.create_span.return_value = mock_tool_span

    # Create a decorated function that uses trace.get_current_span()
    @tool(name="test_tool", tool_type="search")
    def test_function(arg1, arg2=None):
        current_span = trace.get_current_span()
        return f"{arg1}:{arg2}:{current_span}"

    # Mock trace.get_current_span inside the function to return our tool span
    with patch("opentelemetry.trace.get_current_span", side_effect=[mock_parent_span, mock_tool_span.span]):
        # Call and test
        result = test_function("test1", "test2")

    # Verify that TracingCore was called correctly
    mock_instance.create_span.assert_called_once_with(
        kind="tool", name="test_tool", parent=mock_parent_span, attributes={}, immediate_export=True, tool_type="search"
    )

    # Verify the span was started
    mock_tool_span.start.assert_called_once()

    # Result should include the mock_span
    assert "test1:test2:" in result
    assert str(mock_tool_span.span) in result

    # Test set_input and set_output
    mock_tool_span.set_input.assert_called_once()
    mock_tool_span.set_output.assert_called_once()

    # Test when no parent span is found
    mock_get_current_span.return_value = None
    result = test_function("test1", "test2")
    assert result == "test1:test2:None"
