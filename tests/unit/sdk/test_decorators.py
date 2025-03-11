import unittest
from unittest.mock import patch, MagicMock, ANY

from opentelemetry import trace
from opentelemetry.trace import Span, SpanContext, TraceFlags

from agentops.sdk.decorators.session import session
from agentops.sdk.decorators.agent import agent
from agentops.sdk.decorators.tool import tool
from agentops.sdk.spans.session import SessionSpan
from agentops.sdk.spans.agent import AgentSpan
from agentops.sdk.spans.tool import ToolSpan


class TestSessionDecorator(unittest.TestCase):
    """Test the session decorator."""

    @patch("agentops.sdk.decorators.session.TracingCore")
    def test_class_decoration(self, mock_tracing_core):
        """Test decorating a class."""
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
        self.assertEqual(test.arg1, "test1")
        self.assertEqual(test.arg2, "test2")
        self.assertEqual(test._session_span, mock_span)
        
        # Verify that TracingCore was called correctly
        mock_instance.create_span.assert_called_once_with(
            kind="session",
            name="test_session",
            attributes={},
            immediate_export=True,
            config=ANY,
            tags=["tag1", "tag2"]
        )
        
        # Verify the span was started
        mock_span.start.assert_called_once()

    @patch("agentops.sdk.decorators.session.TracingCore")
    def test_function_decoration(self, mock_tracing_core):
        """Test decorating a function."""
        # Setup mock
        mock_span = MagicMock(spec=SessionSpan)
        mock_span.span = MagicMock(spec=Span)
        mock_instance = mock_tracing_core.get_instance.return_value
        mock_instance.create_span.return_value = mock_span
        
        # Create a decorated function
        @session(name="test_session", tags=["tag1", "tag2"])
        def test_function(arg1, arg2=None, session_span=None):
            return f"{arg1}:{arg2}:{session_span}"
        
        # Call and test
        result = test_function("test1", "test2")
        
        # Verify that TracingCore was called correctly
        mock_instance.create_span.assert_called_once_with(
            kind="session",
            name="test_session",
            attributes={},
            immediate_export=True,
            config=ANY,
            tags=["tag1", "tag2"]
        )
        
        # Verify the span was started and ended
        mock_span.start.assert_called_once()
        mock_span.end.assert_called_once_with("SUCCEEDED")
        
        # Result should include the mock_span
        self.assertIn("test1:test2:", result)
        self.assertIn(str(mock_span), result)


class TestAgentDecorator(unittest.TestCase):
    """Test the agent decorator."""

    @patch("agentops.sdk.decorators.agent.trace.get_current_span")
    @patch("agentops.sdk.decorators.agent.TracingCore")
    def test_class_decoration(self, mock_tracing_core, mock_get_current_span):
        """Test decorating a class."""
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
        self.assertEqual(test.arg1, "test1")
        self.assertEqual(test.arg2, "test2")
        self.assertEqual(test._agent_span, mock_agent_span)
        
        # Verify that trace.get_current_span was called
        mock_get_current_span.assert_called()
        
        # Verify that TracingCore was called correctly
        mock_instance.create_span.assert_called_once_with(
            kind="agent",
            name="test_agent",
            parent=mock_parent_span,
            attributes={},
            immediate_export=True,
            agent_type="assistant"
        )
        
        # Verify the span was started
        mock_agent_span.start.assert_called_once()
        
        # Test a method call
        result = test.method()
        self.assertEqual(result, "test1:test2")

    @patch("agentops.sdk.decorators.agent.trace.get_current_span")
    @patch("agentops.sdk.decorators.agent.TracingCore")
    def test_function_decoration(self, mock_tracing_core, mock_get_current_span):
        """Test decorating a function."""
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
        
        # Create a decorated function
        @agent(name="test_agent", agent_type="assistant")
        def test_function(arg1, arg2=None, agent_span=None):
            return f"{arg1}:{arg2}:{agent_span}"
        
        # Call and test
        result = test_function("test1", "test2")
        
        # Verify that trace.get_current_span was called
        mock_get_current_span.assert_called()
        
        # Verify that TracingCore was called correctly
        mock_instance.create_span.assert_called_once_with(
            kind="agent",
            name="test_agent",
            parent=mock_parent_span,
            attributes={},
            immediate_export=True,
            agent_type="assistant"
        )
        
        # Verify the span was started
        mock_agent_span.start.assert_called_once()
        
        # Result should include the mock_span
        self.assertIn("test1:test2:", result)
        self.assertIn(str(mock_agent_span), result)
        
        # Test when no parent span is found
        mock_get_current_span.return_value = None
        result = test_function("test1", "test2")
        self.assertEqual(result, "test1:test2:None")


class TestToolDecorator(unittest.TestCase):
    """Test the tool decorator."""

    @patch("agentops.sdk.decorators.tool.trace.get_current_span")
    @patch("agentops.sdk.decorators.tool.TracingCore")
    def test_function_decoration(self, mock_tracing_core, mock_get_current_span):
        """Test decorating a function."""
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
        
        # Create a decorated function
        @tool(name="test_tool", tool_type="search")
        def test_function(arg1, arg2=None, tool_span=None):
            return f"{arg1}:{arg2}:{tool_span}"
        
        # Call and test
        result = test_function("test1", "test2")
        
        # Verify that trace.get_current_span was called
        mock_get_current_span.assert_called()
        
        # Verify that TracingCore was called correctly
        mock_instance.create_span.assert_called_once_with(
            kind="tool",
            name="test_tool",
            parent=mock_parent_span,
            attributes={},
            immediate_export=True,
            tool_type="search"
        )
        
        # Verify the span was started
        mock_tool_span.start.assert_called_once()
        
        # Result should include the mock_span
        self.assertIn("test1:test2:", result)
        self.assertIn(str(mock_tool_span), result)
        
        # Test set_input and set_output
        mock_tool_span.set_input.assert_called_once()
        mock_tool_span.set_output.assert_called_once()
        
        # Test when no parent span is found
        mock_get_current_span.return_value = None
        result = test_function("test1", "test2")
        self.assertEqual(result, "test1:test2:None")


if __name__ == "__main__":
    unittest.main() 