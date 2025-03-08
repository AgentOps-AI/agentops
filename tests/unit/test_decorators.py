"""Tests for AgentOps decorators (agent, tool, span, create_span)."""

import asyncio
from unittest.mock import patch, MagicMock, Mock
import inspect

import pytest
from opentelemetry.trace import Span, NonRecordingSpan, SpanContext

import agentops
from agentops.decorators import agent, tool, span, create_span, current_span, add_span_attribute
from agentops.semconv import SpanKind, AgentAttributes, ToolAttributes, CoreAttributes, ToolStatus

from agentops.decorators import session
from agentops.session.session import SessionState

def test_session_basic():
    """Test basic @session decorator usage."""
    with patch('agentops.start_session') as mock_start, \
         patch('agentops.end_session') as mock_end:
        mock_start.return_value = True

        @session
        def test_func():
            return "success"
        
        result = test_func()
        
        assert result == "success"
        mock_start.assert_called_once_with(None)
        mock_end.assert_called_once_with(
            end_state=str(SessionState.SUCCEEDED),
            is_auto_end=True
        )


def test_session_with_tags():
    """Test @session decorator with tags."""
    test_tags = ["test_tag1", "test_tag2"]
    
    with patch('agentops.start_session') as mock_start, \
         patch('agentops.end_session') as mock_end:
        mock_start.return_value = True

        @session(test_tags)
        def test_func():
            return "tagged"
        
        result = test_func()
        
        assert result == "tagged"
        mock_start.assert_called_once_with(test_tags)
        mock_end.assert_called_once_with(
            end_state=str(SessionState.SUCCEEDED),
            is_auto_end=True
        )


def test_session_with_exception():
    """Test @session decorator when wrapped function raises an exception."""
    with patch('agentops.start_session') as mock_start, \
         patch('agentops.end_session') as mock_end:
        mock_start.return_value = True

        @session
        def failing_func():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError, match="Test error"):
            failing_func()
        
        mock_start.assert_called_once_with(None)
        mock_end.assert_called_once_with(
            end_state=str(SessionState.SUCCEEDED),
            is_auto_end=True
        )


def test_session_with_args():
    """Test @session decorator with function arguments."""
    with patch('agentops.start_session') as mock_start, \
         patch('agentops.end_session') as mock_end:
        mock_start.return_value = True

        @session
        def func_with_args(x: int, y: int, name: str = "default") -> str:
            return f"{x} + {y} = {x + y}, name: {name}"
        
        result = func_with_args(1, 2, name="test")
        
        assert result == "1 + 2 = 3, name: test"
        mock_start.assert_called_once_with(None)
        mock_end.assert_called_once_with(
            end_state=str(SessionState.SUCCEEDED),
            is_auto_end=True
        )


def test_session_no_active_session():
    """Test @session decorator when no session is started."""
    with patch('agentops.start_session') as mock_start, \
         patch('agentops.end_session') as mock_end:
        mock_start.return_value = None  # Simulate no session started

        @session
        def test_func():
            return "no session"
        
        result = test_func()
        
        assert result == "no session"
        mock_start.assert_called_once_with(None)
        mock_end.assert_not_called()  # end_session shouldn't be called if no session was started

# ===== Agent Decorator Tests =====

def test_agent_decorator_basic():
    """Test basic @agent decorator usage."""
    with patch('agentops.decorators._tracer') as mock_tracer:
        mock_span = MagicMock(spec=Span)
        mock_start_span = MagicMock()
        mock_start_span.return_value.__enter__.return_value = mock_span
        mock_tracer.start_as_current_span = mock_start_span

        @agent(name="test_agent", role="test_role")
        class TestAgent:
            def __init__(self, model="test-model"):
                self.model = model
            
            def test_method(self):
                return "test_result"
        
        # Create an instance of the decorated class
        test_agent = TestAgent(model="gpt-4")
        
        # Check that the span was created with the right attributes
        mock_start_span.assert_called_once()
        call_args = mock_start_span.call_args[1]
        assert call_args["name"] == "test_agent"
        assert "attributes" in call_args
        attributes = call_args["attributes"]
        assert attributes.get("span.kind") == SpanKind.AGENT
        assert attributes.get(AgentAttributes.AGENT_ROLE) == "test_role"
        
        # Check that the original functionality works
        assert test_agent.model == "gpt-4"
        assert test_agent.test_method() == "test_result"


def test_agent_decorator_with_tools():
    """Test @agent decorator with tools specified."""
    with patch('agentops.decorators._tracer') as mock_tracer:
        mock_span = MagicMock(spec=Span)
        mock_start_span = MagicMock()
        mock_start_span.return_value.__enter__.return_value = mock_span
        mock_tracer.start_as_current_span = mock_start_span

        @agent(name="test_agent", tools=["tool1", "tool2"])
        class TestAgent:
            def __init__(self):
                pass
        
        # Create an instance of the decorated class
        test_agent = TestAgent()
        
        # Check that the tools were added as attributes
        call_args = mock_start_span.call_args[1]
        attributes = call_args["attributes"]
        # The tools are stored as a list, not a JSON string
        assert attributes.get(AgentAttributes.AGENT_TOOLS) == ["tool1", "tool2"]


def test_agent_decorator_with_models():
    """Test @agent decorator with models specified."""
    with patch('agentops.decorators._tracer') as mock_tracer:
        mock_span = MagicMock(spec=Span)
        mock_start_span = MagicMock()
        mock_start_span.return_value.__enter__.return_value = mock_span
        mock_tracer.start_as_current_span = mock_start_span

        @agent(name="test_agent", models=["model1", "model2"])
        class TestAgent:
            def __init__(self):
                pass
        
        # Create an instance of the decorated class
        test_agent = TestAgent()
        
        # Check that the models were added as attributes
        call_args = mock_start_span.call_args[1]
        attributes = call_args["attributes"]
        # The models are stored as a list, not a JSON string
        assert attributes.get(AgentAttributes.AGENT_MODELS) == ["model1", "model2"]


def test_agent_decorator_with_custom_attributes():
    """Test @agent decorator with custom attributes."""
    with patch('agentops.decorators._tracer') as mock_tracer:
        mock_span = MagicMock(spec=Span)
        mock_start_span = MagicMock()
        mock_start_span.return_value.__enter__.return_value = mock_span
        mock_tracer.start_as_current_span = mock_start_span

        @agent(
            name="test_agent",
            attributes={"custom_attr": "custom_value"}
        )
        class TestAgent:
            def __init__(self):
                pass
        
        # Create an instance of the decorated class
        test_agent = TestAgent()
        
        # Check that the custom attributes were added
        call_args = mock_start_span.call_args[1]
        attributes = call_args["attributes"]
        assert attributes.get("custom_attr") == "custom_value"


def test_agent_decorator_cleanup():
    """Test that @agent decorator cleans up properly when the instance is deleted."""
    with patch('agentops.decorators._tracer') as mock_tracer:
        mock_span = MagicMock(spec=Span)
        mock_start_span = MagicMock()
        mock_start_span.return_value.__enter__.return_value = mock_span
        mock_tracer.start_as_current_span = mock_start_span

        @agent(name="test_agent")
        class TestAgent:
            def __init__(self):
                pass
        
        # Create an instance of the decorated class
        test_agent = TestAgent()
        
        # Since we can't easily test __del__, we'll just verify that the agent has the expected attributes
        assert hasattr(test_agent, "_agentops_span")
        
        # We can also verify that the span was created with the right attributes
        mock_start_span.assert_called_once()
        call_args = mock_start_span.call_args[1]
        assert call_args["name"] == "test_agent"


# ===== Tool Decorator Tests =====

def test_tool_decorator_basic():
    """Test basic @tool decorator usage."""
    with patch('agentops.decorators._tracer') as mock_tracer:
        mock_span = MagicMock(spec=Span)
        mock_start_span = MagicMock()
        mock_start_span.return_value.__enter__.return_value = mock_span
        mock_tracer.start_as_current_span = mock_start_span

        @tool(name="test_tool", description="A test tool")
        def test_function(a, b):
            return a + b
        
        # Call the decorated function
        result = test_function(1, 2)
        
        # Check the result
        assert result == 3
        
        # Check that the span was created with the right attributes
        mock_start_span.assert_called_once()
        call_args = mock_start_span.call_args[1]
        assert call_args["name"] == "test_tool"
        assert "attributes" in call_args
        attributes = call_args["attributes"]
        assert attributes.get("span.kind") == SpanKind.TOOL
        assert attributes.get(ToolAttributes.TOOL_DESCRIPTION) == "A test tool"
        
        # Check that the tool parameters were captured
        assert ToolAttributes.TOOL_PARAMETERS in attributes
        
        # Check that the tool status was set to succeeded (lowercase in the actual implementation)
        mock_span.set_attribute.assert_any_call(ToolAttributes.TOOL_STATUS, "succeeded")


def test_tool_decorator_with_exception():
    """Test @tool decorator when the function raises an exception."""
    with patch('agentops.decorators._tracer') as mock_tracer:
        mock_span = MagicMock(spec=Span)
        mock_start_span = MagicMock()
        mock_start_span.return_value.__enter__.return_value = mock_span
        mock_tracer.start_as_current_span = mock_start_span

        @tool(name="failing_tool")
        def failing_function():
            raise ValueError("Test error")
        
        # Call the decorated function and expect an exception
        with pytest.raises(ValueError, match="Test error"):
            failing_function()
        
        # Check that the error was recorded in the span
        mock_span.set_attribute.assert_any_call(CoreAttributes.ERROR_TYPE, "ValueError")
        mock_span.set_attribute.assert_any_call(CoreAttributes.ERROR_MESSAGE, "Test error")
        # Check that the tool status was set to failed (lowercase in the actual implementation)
        mock_span.set_attribute.assert_any_call(ToolAttributes.TOOL_STATUS, "failed")


def test_tool_decorator_capture_args():
    """Test @tool decorator with argument capturing."""
    with patch('agentops.decorators._tracer') as mock_tracer:
        mock_span = MagicMock(spec=Span)
        mock_start_span = MagicMock()
        mock_start_span.return_value.__enter__.return_value = mock_span
        mock_tracer.start_as_current_span = mock_start_span

        @tool(name="test_tool", capture_args=True)
        def test_function(a, b, c="default"):
            return f"{a}_{b}_{c}"
        
        # Call the decorated function
        result = test_function("test", 123, c="custom")
        
        # Check the result
        assert result == "test_123_custom"
        
        # Check that the arguments were captured
        call_args = mock_start_span.call_args[1]
        attributes = call_args["attributes"]
        tool_params = attributes.get(ToolAttributes.TOOL_PARAMETERS)
        assert "a" in tool_params
        assert "b" in tool_params
        assert "c" in tool_params


def test_tool_decorator_no_capture_args():
    """Test @tool decorator with argument capturing disabled."""
    with patch('agentops.decorators._tracer') as mock_tracer:
        mock_span = MagicMock(spec=Span)
        mock_start_span = MagicMock()
        mock_start_span.return_value.__enter__.return_value = mock_span
        mock_tracer.start_as_current_span = mock_start_span

        @tool(name="test_tool", capture_args=False)
        def test_function(a, b):
            return a + b
        
        # Call the decorated function
        result = test_function(1, 2)
        
        # Check the result
        assert result == 3
        
        # Check that the arguments were not captured
        call_args = mock_start_span.call_args[1]
        attributes = call_args["attributes"]
        assert ToolAttributes.TOOL_PARAMETERS not in attributes


# ===== Span Decorator Tests =====

def test_span_decorator_sync():
    """Test @span decorator with a synchronous function."""
    with patch('agentops.decorators._tracer') as mock_tracer:
        mock_span = MagicMock(spec=Span)
        mock_start_span = MagicMock()
        mock_start_span.return_value.__enter__.return_value = mock_span
        mock_tracer.start_as_current_span = mock_start_span

        @span(name="test_span", kind=SpanKind.WORKFLOW_STEP)
        def test_function(a, b):
            return a * b
        
        # Call the decorated function
        result = test_function(3, 4)
        
        # Check the result
        assert result == 12
        
        # Check that the span was created with the right attributes
        mock_start_span.assert_called_once()
        call_args = mock_start_span.call_args[1]
        assert call_args["name"] == "test_span"
        assert "attributes" in call_args
        attributes = call_args["attributes"]
        assert attributes.get("span.kind") == SpanKind.WORKFLOW_STEP


@pytest.mark.asyncio
async def test_span_decorator_async():
    """Test @span decorator with an asynchronous function."""
    with patch('agentops.decorators._tracer') as mock_tracer:
        mock_span = MagicMock(spec=Span)
        mock_start_span = MagicMock()
        mock_start_span.return_value.__enter__.return_value = mock_span
        mock_tracer.start_as_current_span = mock_start_span

        @span(name="async_span", kind=SpanKind.AGENT_ACTION)
        async def async_function(a, b):
            await asyncio.sleep(0.01)  # Small delay
            return a + b
        
        # Call the decorated function
        result = await async_function(5, 6)
        
        # Check the result
        assert result == 11
        
        # Check that the span was created with the right attributes
        mock_start_span.assert_called_once()
        call_args = mock_start_span.call_args[1]
        assert call_args["name"] == "async_span"
        assert "attributes" in call_args
        attributes = call_args["attributes"]
        assert attributes.get("span.kind") == SpanKind.AGENT_ACTION


def test_span_decorator_method():
    """Test @span decorator with a class method."""
    with patch('agentops.decorators._tracer') as mock_tracer:
        mock_span = MagicMock(spec=Span)
        mock_start_span = MagicMock()
        mock_start_span.return_value.__enter__.return_value = mock_span
        mock_tracer.start_as_current_span = mock_start_span

        class TestClass:
            @span(name="method_span")
            def test_method(self, x):
                return x * 2
        
        # Create an instance and call the decorated method
        instance = TestClass()
        result = instance.test_method(5)
        
        # Check the result
        assert result == 10
        
        # Check that the span was created
        mock_start_span.assert_called_once()
        call_args = mock_start_span.call_args[1]
        assert call_args["name"] == "method_span"


def test_span_decorator_with_agent_context():
    """Test @span decorator with a method of an agent class."""
    with patch('agentops.decorators._tracer') as mock_tracer, \
         patch('opentelemetry.context.attach') as mock_attach, \
         patch('opentelemetry.context.detach') as mock_detach:
        
        mock_span = MagicMock(spec=Span)
        mock_start_span = MagicMock()
        mock_start_span.return_value.__enter__.return_value = mock_span
        mock_tracer.start_as_current_span = mock_start_span
        
        mock_token = MagicMock()
        mock_attach.return_value = mock_token
        
        # Create a class with _agentops_context to simulate an agent
        class TestAgentClass:
            def __init__(self):
                self._agentops_context = {"test": "context"}
            
            @span(name="agent_method")
            def test_method(self, x):
                return x * 3
        
        # Create an instance and call the decorated method
        instance = TestAgentClass()
        result = instance.test_method(4)
        
        # Check the result
        assert result == 12
        
        # Check that the context was attached and detached
        mock_attach.assert_called_once_with({"test": "context"})
        mock_detach.assert_called_once_with(mock_token)


def test_span_decorator_with_exception():
    """Test @span decorator when the function raises an exception."""
    with patch('agentops.decorators._tracer') as mock_tracer:
        mock_span = MagicMock(spec=Span)
        mock_start_span = MagicMock()
        mock_start_span.return_value.__enter__.return_value = mock_span
        mock_tracer.start_as_current_span = mock_start_span

        @span(name="failing_span")
        def failing_function(x):
            raise ValueError("Test span error")
        
        # Call the decorated function and expect an exception
        with pytest.raises(ValueError, match="Test span error"):
            failing_function(1)
        
        # Check that the error was recorded in the span
        mock_span.set_attribute.assert_any_call(CoreAttributes.ERROR_TYPE, "ValueError")
        mock_span.set_attribute.assert_any_call(CoreAttributes.ERROR_MESSAGE, "Test span error")


# ===== Create Span Context Manager Tests =====

def test_create_span_basic():
    """Test basic create_span context manager usage."""
    with patch('agentops.decorators._tracer') as mock_tracer:
        mock_span = MagicMock(spec=Span)
        mock_start_span = MagicMock()
        mock_start_span.return_value.__enter__.return_value = mock_span
        mock_tracer.start_as_current_span = mock_start_span

        # Use the context manager
        with create_span("test_manual_span", kind=SpanKind.WORKFLOW_STEP) as span:
            # The span is the mock span
            span.set_attribute("custom_attr", "custom_value")
        
        # Check that the span was created with the right attributes
        mock_start_span.assert_called_once()
        call_args = mock_start_span.call_args[1]
        assert call_args["name"] == "test_manual_span"
        assert "attributes" in call_args
        attributes = call_args["attributes"]
        assert attributes.get("span.kind") == SpanKind.WORKFLOW_STEP
        
        # Check that the custom attribute was set
        mock_span.set_attribute.assert_called_with("custom_attr", "custom_value")


def test_create_span_with_exception():
    """Test create_span context manager when an exception is raised."""
    with patch('agentops.decorators._tracer') as mock_tracer:
        mock_span = MagicMock(spec=Span)
        mock_start_span = MagicMock()
        mock_start_span.return_value.__enter__.return_value = mock_span
        mock_tracer.start_as_current_span = mock_start_span

        # Use the context manager with an exception
        with pytest.raises(ValueError, match="Test context error"):
            with create_span("failing_span") as span:
                raise ValueError("Test context error")
        
        # Check that the error was recorded in the span
        mock_span.set_attribute.assert_any_call(CoreAttributes.ERROR_TYPE, "ValueError")
        mock_span.set_attribute.assert_any_call(CoreAttributes.ERROR_MESSAGE, "Test context error")


def test_create_span_with_attributes():
    """Test create_span context manager with custom attributes."""
    with patch('agentops.decorators._tracer') as mock_tracer:
        mock_span = MagicMock(spec=Span)
        mock_start_span = MagicMock()
        mock_start_span.return_value.__enter__.return_value = mock_span
        mock_tracer.start_as_current_span = mock_start_span

        # Use the context manager with attributes
        with create_span(
            "span_with_attrs",
            kind=SpanKind.TOOL,
            attributes={"attr1": "value1"},
            attr2="value2"
        ) as span:
            pass
        
        # Check that the attributes were added
        call_args = mock_start_span.call_args[1]
        attributes = call_args["attributes"]
        assert attributes.get("attr1") == "value1"
        assert attributes.get("attr2") == "value2"
        assert attributes.get("span.kind") == SpanKind.TOOL


# ===== Helper Function Tests =====

def test_current_span():
    """Test the current_span helper function."""
    with patch('opentelemetry.trace.get_current_span') as mock_get_span:
        mock_span = MagicMock(spec=Span)
        mock_get_span.return_value = mock_span
        
        # Call the helper function
        result = current_span()
        
        # Check the result
        assert result is mock_span
        mock_get_span.assert_called_once()


def test_add_span_attribute():
    """Test the add_span_attribute helper function."""
    with patch('agentops.decorators.current_span') as mock_current_span:
        mock_span = MagicMock(spec=Span)
        mock_current_span.return_value = mock_span
        
        # Call the helper function
        add_span_attribute("test_key", "test_value")
        
        # Check that the attribute was set on the current span
        mock_span.set_attribute.assert_called_once_with("test_key", "test_value") 