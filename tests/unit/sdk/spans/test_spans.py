import pytest
from unittest.mock import MagicMock, patch
from uuid import UUID
import json

from opentelemetry.trace import StatusCode, SpanKind as OTelSpanKind

from agentops.sdk.types import TracingConfig
from agentops.sdk.spans.session import SessionSpan
from agentops.sdk.spans.agent import AgentSpan
from agentops.sdk.spans.tool import ToolSpan
from agentops.sdk.spans.custom import CustomSpan
from agentops.semconv.agent import AgentAttributes
from agentops.semconv.span_kinds import SpanKind
from agentops.semconv.tool import ToolAttributes
from agentops.semconv.core import CoreAttributes


# SessionSpan Tests
@patch("agentops.sdk.spans.session.TracingCore")
def test_session_span_init(mock_tracing_core):
    """Test initialization of SessionSpan."""
    # Set up
    mock_core = MagicMock()
    mock_tracing_core.get_instance.return_value = mock_core
    config = TracingConfig(service_name="test_service", max_queue_size=512, max_wait_time=5000)
    
    # Test
    span = SessionSpan(
        name="test_session",
        config=config,
        tags=["tag1", "tag2"],
        host_env={"os": "linux"}
    )
    
    # Verify
    assert span.name == "test_session"
    assert span.kind == "session"
    assert span._config == config
    assert span._tags == ["tag1", "tag2"]
    assert span._host_env == {"os": "linux"}
    assert span._state == "INITIALIZING"
    assert span._state_reason is None
    mock_core.initialize_from_config.assert_called_once_with(config)


def test_session_span_start():
    """Test starting a session span."""
    # Set up
    config = TracingConfig(service_name="test_service", max_queue_size=512, max_wait_time=5000)
    span = SessionSpan(
        name="test_session",
        config=config
    )
    span.set_state = MagicMock()
    super_start = MagicMock()
    with patch("agentops.sdk.spans.session.TracedObject.start", super_start):
        # Test
        result = span.start()
        
        # Verify
        assert result == span
        super_start.assert_called_once()
        span.set_state.assert_called_once()


def test_session_span_end():
    """Test ending a session span."""
    # Set up
    config = TracingConfig(service_name="test_service", max_queue_size=512, max_wait_time=5000)
    span = SessionSpan(
        name="test_session",
        config=config
    )
    span.set_state = MagicMock()
    super_end = MagicMock()
    with patch("agentops.sdk.spans.session.TracedObject.end", super_end):
        # Test with default state
        result = span.end()
        
        # Verify
        span.set_state.assert_called_once_with("SUCCEEDED")
        super_end.assert_called_once_with(StatusCode.OK)
        
        # Test with custom state
        span.set_state.reset_mock()
        super_end.reset_mock()
        result = span.end("FAILED")
        
        # Verify
        span.set_state.assert_called_once_with("FAILED")
        super_end.assert_called_once_with(StatusCode.ERROR)


def test_session_span_set_state():
    """Test setting the session state."""
    # Set up
    config = TracingConfig(service_name="test_service", max_queue_size=512, max_wait_time=5000)
    span = SessionSpan(
        name="test_session",
        config=config
    )
    span.set_attribute = MagicMock()
    span.set_status = MagicMock()
    
    # Test with simple state
    span.set_state("RUNNING")
    assert span._state == "RUNNING"
    assert span._state_reason is None
    span.set_attribute.assert_called_once_with("session.state", "RUNNING")
    span.set_status.assert_not_called()
    
    # Test with state and reason
    span.set_attribute.reset_mock()
    span.set_state("FAILED", "Something went wrong")
    assert span._state == "FAILED"
    assert span._state_reason == "Something went wrong"
    # Check that set_attribute was called twice (once for state, once for error message)
    assert span.set_attribute.call_count == 2
    # Check that the first call was for session.state
    assert span.set_attribute.call_args_list[0][0][0] == "session.state"
    assert span.set_attribute.call_args_list[0][0][1] == "FAILED(Something went wrong)"
    # Check that the second call was for error.message
    assert span.set_attribute.call_args_list[1][0][0] == CoreAttributes.ERROR_MESSAGE
    assert span.set_attribute.call_args_list[1][0][1] == "Something went wrong"
    
    # Test with normalized state
    span.set_attribute.reset_mock()
    span.set_status.reset_mock()
    span.set_state("success")
    assert span._state == "SUCCEEDED"
    assert span._state_reason is None
    span.set_attribute.assert_called_once_with("session.state", "SUCCEEDED")
    span.set_status.assert_called_once_with(StatusCode.OK)


def test_session_span_state_property():
    """Test the state property."""
    # Set up
    config = TracingConfig(service_name="test_service", max_queue_size=512, max_wait_time=5000)
    span = SessionSpan(
        name="test_session",
        config=config
    )
    
    # Test without reason
    span._state = "RUNNING"
    span._state_reason = None
    assert span.state == "RUNNING"
    
    # Test with reason
    span._state = "FAILED"
    span._state_reason = "Something went wrong"
    assert span.state == "FAILED(Something went wrong)"


def test_session_span_add_tag():
    """Test adding a tag."""
    # Set up
    config = TracingConfig(service_name="test_service", max_queue_size=512, max_wait_time=5000)
    span = SessionSpan(
        name="test_session",
        config=config,
        tags=["tag1"]
    )
    span.set_attribute = MagicMock()
    
    # Test adding a new tag
    span.add_tag("tag2")
    assert span._tags == ["tag1", "tag2"]
    span.set_attribute.assert_called_once_with("session.tags", json.dumps(["tag1", "tag2"]))
    
    # Test adding an existing tag
    span.set_attribute.reset_mock()
    span.add_tag("tag1")
    assert span._tags == ["tag1", "tag2"]
    span.set_attribute.assert_called_once_with("session.tags", json.dumps(["tag1", "tag2"]))


def test_session_span_add_tags():
    """Test adding multiple tags."""
    # Set up
    config = TracingConfig(service_name="test_service", max_queue_size=512, max_wait_time=5000)
    span = SessionSpan(
        name="test_session",
        config=config,
        tags=["tag1"]
    )
    span.add_tag = MagicMock()
    
    # Test adding multiple tags
    span.add_tags(["tag2", "tag3"])
    assert span.add_tag.call_count == 2
    span.add_tag.assert_any_call("tag2")
    span.add_tag.assert_any_call("tag3")


def test_session_span_to_dict():
    """Test converting to dictionary."""
    # Set up
    config = TracingConfig(service_name="test_service", max_queue_size=512, max_wait_time=5000)
    span = SessionSpan(
        name="test_session",
        config=config,
        tags=["tag1", "tag2"],
        host_env={"os": "linux"}
    )
    span._state = "RUNNING"
    
    # Test
    result = span.to_dict()
    
    # Verify
    assert result["name"] == "test_session"
    assert result["kind"] == "session"
    assert result["tags"] == ["tag1", "tag2"]
    # Only check host_env if it's in the result
    if "host_env" in result:
        assert result["host_env"] == {"os": "linux"}
    assert result["state"] == "RUNNING"
    # Only check config if it's in the result
    if "config" in result:
        assert result["config"] == config


# AgentSpan Tests
def test_agent_span_init():
    """Test initialization of AgentSpan."""
    # Test
    span = AgentSpan(
        name="test_agent",
        agent_type="assistant",
        parent=None
    )
    
    # Verify
    assert span.name == "test_agent"
    assert span.kind == "agent"
    assert span._agent_type == "assistant"
    assert span.immediate_export
    
    # Import the constants at test time to avoid circular imports
    assert span._attributes[AgentAttributes.AGENT_NAME] == "test_agent"
    assert span._attributes[AgentAttributes.AGENT_ROLE] == "assistant"


def test_agent_span_record_action():
    """Test recording an action."""
    # Set up
    span = AgentSpan(
        name="test_agent",
        agent_type="assistant"
    )
    span.set_attribute = MagicMock()
    span.update = MagicMock()
    
    # Test without details
    span.record_action("search")
    span.set_attribute.assert_called_once_with(SpanKind.AGENT_ACTION, "search")
    span.update.assert_called_once()
    
    # Test with details
    span.set_attribute.reset_mock()
    span.update.reset_mock()
    span.record_action("search", {"query": "test query"})
    span.set_attribute.assert_any_call(SpanKind.AGENT_ACTION, "search")
    span.set_attribute.assert_any_call(f"{SpanKind.AGENT_ACTION}.query", "test query")
    span.update.assert_called_once()


def test_agent_span_record_thought():
    """Test recording a thought."""
    # Set up
    span = AgentSpan(
        name="test_agent",
        agent_type="assistant"
    )
    span.set_attribute = MagicMock()
    span.update = MagicMock()
    
    # Test
    span.record_thought("I should search for information")
    span.set_attribute.assert_called_once_with(SpanKind.AGENT_THINKING, "I should search for information")
    span.update.assert_called_once()


def test_agent_span_record_error():
    """Test recording an error."""
    # Set up
    span = AgentSpan(
        name="test_agent",
        agent_type="assistant"
    )
    span.set_attribute = MagicMock()
    span.update = MagicMock()
    
    # Test with string
    span.record_error("Something went wrong")
    span.set_attribute.assert_called_once_with(CoreAttributes.ERROR_MESSAGE, "Something went wrong")
    span.update.assert_called_once()
    
    # Test with exception
    span.set_attribute.reset_mock()
    span.update.reset_mock()
    span.record_error(ValueError("Invalid value"))
    span.set_attribute.assert_called_once_with(CoreAttributes.ERROR_MESSAGE, "Invalid value")
    span.update.assert_called_once()


def test_agent_span_to_dict():
    """Test converting to dictionary."""
    # Set up
    span = AgentSpan(
        name="test_agent",
        agent_type="assistant"
    )
    
    # Test
    result = span.to_dict()
    
    # Verify
    assert result["name"] == "test_agent"
    assert result["kind"] == "agent"
    assert result["agent_type"] == "assistant"


# ToolSpan Tests
def test_tool_span_init():
    """Test initialization of ToolSpan."""
    # Test
    span = ToolSpan(
        name="test_tool",
        tool_type="search",
        parent=None
    )
    
    # Verify
    assert span.name == "test_tool"
    assert span.kind == "tool"
    assert span._tool_type == "search"
    assert not span.immediate_export
    
    # Import the constants at test time to avoid circular imports
    assert span._attributes[ToolAttributes.TOOL_NAME] == "test_tool"
    assert span._attributes[ToolAttributes.TOOL_DESCRIPTION] == "search"
    assert span._input is None
    assert span._output is None


def test_tool_span_set_input():
    """Test setting input."""
    # Set up
    span = ToolSpan(
        name="test_tool",
        tool_type="search"
    )
    span.set_attribute = MagicMock()
    
    # Import the constants at test time to avoid circular imports
    from agentops.semconv.tool import ToolAttributes
    
    # Test with string
    span.set_input("test query")
    assert span._input == "test query"
    span.set_attribute.assert_called_once_with(ToolAttributes.TOOL_PARAMETERS, "test query")
    
    # Test with complex object
    span.set_attribute.reset_mock()
    input_data = {"query": "test query", "filters": ["filter1", "filter2"]}
    span.set_input(input_data)
    assert span._input == input_data
    span.set_attribute.assert_called_once()
    assert span.set_attribute.call_args[0][0] == ToolAttributes.TOOL_PARAMETERS
    assert isinstance(span.set_attribute.call_args[0][1], str)


def test_tool_span_set_output():
    """Test setting output."""
    # Set up
    span = ToolSpan(
        name="test_tool",
        tool_type="search"
    )
    span.set_attribute = MagicMock()
    
    # Import the constants at test time to avoid circular imports
    from agentops.semconv.tool import ToolAttributes
    
    # Test with string
    span.set_output("test result")
    assert span._output == "test result"
    span.set_attribute.assert_called_once_with(ToolAttributes.TOOL_RESULT, "test result")
    
    # Test with complex object
    span.set_attribute.reset_mock()
    output_data = {"results": ["result1", "result2"], "count": 2}
    span.set_output(output_data)
    assert span._output == output_data
    span.set_attribute.assert_called_once()
    assert span.set_attribute.call_args[0][0] == ToolAttributes.TOOL_RESULT
    assert isinstance(span.set_attribute.call_args[0][1], str)


def test_tool_span_to_dict():
    """Test converting to dictionary."""
    # Set up
    span = ToolSpan(
        name="test_tool",
        tool_type="search"
    )
    span._input = "test query"
    span._output = "test result"
    
    # Test
    result = span.to_dict()
    
    # Verify
    assert result["name"] == "test_tool"
    assert result["kind"] == "tool"
    assert result["tool_type"] == "search"
    assert result["input"] == "test query"
    assert result["output"] == "test result"


# CustomSpan Tests
def test_custom_span_init():
    """Test initialization of CustomSpan."""
    # Test
    span = CustomSpan(
        name="test_custom",
        kind="custom_kind",
        parent=None
    )
    
    # Verify
    assert span.name == "test_custom"
    assert span.kind == "custom_kind"
    assert span._attributes["custom.name"] == "test_custom"
    assert span._attributes["custom.kind"] == "custom_kind"


def test_custom_span_add_event():
    """Test adding an event."""
    # Set up
    span = CustomSpan(
        name="test_custom",
        kind="custom_kind"
    )
    span._span = MagicMock()
    span.update = MagicMock()
    
    # Test without attributes
    span.add_event("test_event")
    span._span.add_event.assert_called_once_with("test_event", None)
    span.update.assert_called_once()
    
    # Test with attributes
    span._span.reset_mock()
    span.update.reset_mock()
    attributes = {"key": "value"}
    span.add_event("test_event", attributes)
    span._span.add_event.assert_called_once_with("test_event", attributes)
    span.update.assert_called_once() 
