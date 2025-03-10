import pytest
from typing import Dict, Any, List

import agentops
from agentops.sdk.core import TracingCore
from agentops.sdk.decorators.agent import agent
from agentops.sdk.decorators.session import session
from agentops.sdk.decorators.tool import tool
from opentelemetry.trace import StatusCode

from tests.unit.sdk.instrumentation_tester import InstrumentationTester


@pytest.fixture
def instrumentation():
    """Fixture for the instrumentation tester."""
    tester = InstrumentationTester()
    yield tester
    tester.reset()


class TestErrorInstrumentation:
    """Test error handling in instrumentation."""

    def test_session_with_error(self, instrumentation: InstrumentationTester):
        """Test that sessions with errors are properly instrumented."""
        @session(name="error_session")
        class ErrorSession:
            def __init__(self):
                pass

            def run(self):
                raise ValueError("Test error")

        # Create and run a session that raises an error
        error_session = ErrorSession()
        
        # Run the session and catch the error
        with pytest.raises(ValueError, match="Test error"):
            error_session.run()

        # Check the spans
        spans = instrumentation.get_finished_spans()
        assert len(spans) == 1
        
        # Get the session span
        session_spans = instrumentation.get_spans_by_kind("session")
        assert len(session_spans) == 1
        session_span = session_spans[0]
        
        # Check the session span status
        assert session_span.status.status_code == StatusCode.ERROR
        assert session_span.status.description is not None
        assert "Test error" in session_span.status.description

    def test_agent_with_error(self, instrumentation: InstrumentationTester):
        """Test that agents with errors are properly instrumented."""
        @session(name="test_session")
        class TestSession:
            def __init__(self):
                self.agent = ErrorAgent()

            def run(self):
                try:
                    return self.agent.process("test")
                except ValueError:
                    return {"error": "Agent error"}

        @agent(name="error_agent")
        class ErrorAgent:
            def process(self, data: str):
                raise ValueError("Agent error")

        # Create and run a session with an agent that raises an error
        test_session = TestSession()
        result = test_session.run()

        # Check the result
        assert result == {"error": "Agent error"}

        # Check the spans
        spans = instrumentation.get_finished_spans()
        assert len(spans) == 2  # Session span and agent span
        
        # Get the agent span
        agent_spans = instrumentation.get_spans_by_kind("agent")
        assert len(agent_spans) == 1
        agent_span = agent_spans[0]
        
        # Check the agent span status
        assert agent_span.status.status_code == StatusCode.ERROR
        assert agent_span.status.description is not None
        assert "Agent error" in agent_span.status.description

    def test_tool_with_error(self, instrumentation: InstrumentationTester):
        """Test that tools with errors are properly instrumented."""
        @session(name="test_session")
        class TestSession:
            def __init__(self):
                self.agent = TestAgent()

            def run(self):
                try:
                    return self.agent.process("test")
                except ValueError:
                    return {"error": "Tool error"}

        @agent(name="test_agent")
        class TestAgent:
            def process(self, data: str):
                try:
                    result = self.error_tool(data)
                    return {"processed": result}
                except ValueError as e:
                    raise ValueError(f"Tool error: {str(e)}")

            @tool(name="error_tool")
            def error_tool(self, data: str):
                raise ValueError("This tool always fails")

        # Create and run a session with an agent that uses a tool that raises an error
        test_session = TestSession()
        result = test_session.run()

        # Check the result
        assert result == {"error": "Tool error"}

        # Check the spans
        spans = instrumentation.get_finished_spans()
        assert len(spans) == 3  # Session span, agent span, and tool span
        
        # Get the tool span
        tool_spans = instrumentation.get_spans_by_kind("tool")
        assert len(tool_spans) == 1
        tool_span = tool_spans[0]
        
        # Check the tool span status
        assert tool_span.status.status_code == StatusCode.ERROR
        assert tool_span.status.description is not None
        assert "This tool always fails" in tool_span.status.description
        
        # Get the agent span
        agent_spans = instrumentation.get_spans_by_kind("agent")
        assert len(agent_spans) == 1
        agent_span = agent_spans[0]
        
        # Check the agent span status
        assert agent_span.status.status_code == StatusCode.ERROR
        assert agent_span.status.description is not None
        assert "Tool error" in agent_span.status.description

    def test_context_manager_with_error(self, instrumentation: InstrumentationTester):
        """Test that spans used as context managers handle errors properly."""
        # Create a session span directly using the factory
        from agentops.sdk.factory import SpanFactory
        
        # Test with context manager that raises an error
        with pytest.raises(ValueError, match="Context manager error"):
            with SpanFactory.create_session_span(name="context_manager_test"):
                raise ValueError("Context manager error")
        
        # Check the spans
        spans = instrumentation.get_finished_spans()
        assert len(spans) == 1
        
        # Get the session span
        session_span = spans[0]
        
        # Check the session span status
        assert session_span.status.status_code == StatusCode.ERROR
        assert session_span.status.description is not None
        assert "Context manager error" in session_span.status.description

    def test_nested_errors(self, instrumentation: InstrumentationTester):
        """Test that nested spans handle errors properly."""
        @session(name="outer_session")
        class OuterSession:
            def __init__(self):
                self.inner_agent = InnerAgent()

            def run(self):
                try:
                    return self.inner_agent.process("test")
                except ValueError:
                    return {"error": "Caught in outer session"}

        @agent(name="inner_agent")
        class InnerAgent:
            def process(self, data: str):
                # This will raise an error in the tool
                result = self.failing_tool(data)
                return {"processed": result}

            @tool(name="failing_tool")
            def failing_tool(self, data: str):
                raise ValueError("Inner tool error")

        # Create and run the outer session
        outer_session = OuterSession()
        result = outer_session.run()

        # Check the result
        assert result == {"error": "Caught in outer session"}

        # Check the spans
        spans = instrumentation.get_finished_spans()
        assert len(spans) == 3  # Outer session span, inner agent span, and tool span
        
        # Get spans by kind
        session_spans = instrumentation.get_spans_by_kind("session")
        agent_spans = instrumentation.get_spans_by_kind("agent")
        tool_spans = instrumentation.get_spans_by_kind("tool")
        
        assert len(session_spans) == 1
        assert len(agent_spans) == 1
        assert len(tool_spans) == 1
        
        # Check the tool span status
        tool_span = tool_spans[0]
        assert tool_span.status.status_code == StatusCode.ERROR
        assert tool_span.status.description is not None
        assert "Inner tool error" in tool_span.status.description
        
        # Check the agent span status
        agent_span = agent_spans[0]
        assert agent_span.status.status_code == StatusCode.ERROR
        assert agent_span.status.description is not None
        
        # Check the session span status
        # The session should be OK because it caught the error
        session_span = session_spans[0]
        assert session_span.status.status_code == StatusCode.OK 