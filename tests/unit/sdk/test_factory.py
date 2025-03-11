import pytest
from unittest.mock import MagicMock, patch
from uuid import UUID

from agentops.sdk.factory import SpanFactory
from agentops.sdk.spanned import SpannedBase


# Create concrete span classes for testing
class TestSessionSpan(SpannedBase):
    """Test session span class."""
    pass

class TestAgentSpan(SpannedBase):
    """Test agent span class."""
    pass

class TestToolSpan(SpannedBase):
    """Test tool span class."""
    pass


@pytest.fixture
def setup_span_factory():
    """Set up the test by registering test span types."""
    # Register test span types
    SpanFactory._span_types = {}  # Clear existing registrations
    SpanFactory.register_span_type("session", TestSessionSpan)
    SpanFactory.register_span_type("agent", TestAgentSpan)
    SpanFactory.register_span_type("tool", TestToolSpan)
    yield
    # Clean up after tests
    SpanFactory._span_types = {}


def test_register_span_type(setup_span_factory):
    """Test registering a span type."""
    # Test registering a new span type
    class CustomSpan(SpannedBase):
        pass
    
    SpanFactory.register_span_type("custom", CustomSpan)
    assert SpanFactory._span_types["custom"] == CustomSpan
    
    # Test overriding an existing span type
    class NewSessionSpan(SpannedBase):
        pass
    
    SpanFactory.register_span_type("session", NewSessionSpan)
    assert SpanFactory._span_types["session"] == NewSessionSpan


def test_create_span(setup_span_factory):
    """Test creating a span."""
    # Test creating a session span
    span = SpanFactory.create_span(
        kind="session",
        name="test_session",
        auto_start=False
    )
    assert isinstance(span, TestSessionSpan)
    assert span.name == "test_session"
    assert span.kind == "session"
    assert not span.is_started
    
    # Test creating a span with auto_start=True
    with patch.object(TestAgentSpan, "start") as mock_start:
        span = SpanFactory.create_span(
            kind="agent",
            name="test_agent",
            auto_start=True
        )
        mock_start.assert_called_once()
    
    # Test creating a span with unknown kind
    with pytest.raises(ValueError):
        SpanFactory.create_span(
            kind="unknown",
            name="test_unknown"
        )


def test_create_session_span(setup_span_factory):
    """Test creating a session span."""
    with patch.object(SpanFactory, "create_span") as mock_create_span:
        SpanFactory.create_session_span(
            name="test_session",
            attributes={"key": "value"},
            auto_start=True,
            immediate_export=True
        )
        mock_create_span.assert_called_once_with(
            kind="session",
            name="test_session",
            parent=None,
            attributes={"key": "value"},
            auto_start=True,
            immediate_export=True
        )


def test_create_agent_span(setup_span_factory):
    """Test creating an agent span."""
    with patch.object(SpanFactory, "create_span") as mock_create_span:
        parent = MagicMock()
        SpanFactory.create_agent_span(
            name="test_agent",
            parent=parent,
            attributes={"key": "value"},
            auto_start=True,
            immediate_export=True
        )
        mock_create_span.assert_called_once_with(
            kind="agent",
            name="test_agent",
            parent=parent,
            attributes={"key": "value"},
            auto_start=True,
            immediate_export=True
        )


def test_create_tool_span(setup_span_factory):
    """Test creating a tool span."""
    with patch.object(SpanFactory, "create_span") as mock_create_span:
        parent = MagicMock()
        SpanFactory.create_tool_span(
            name="test_tool",
            parent=parent,
            attributes={"key": "value"},
            auto_start=True,
            immediate_export=False
        )
        mock_create_span.assert_called_once_with(
            kind="tool",
            name="test_tool",
            parent=parent,
            attributes={"key": "value"},
            auto_start=True,
            immediate_export=False
        )


def test_create_custom_span(setup_span_factory):
    """Test creating a custom span."""
    with patch.object(SpanFactory, "create_span") as mock_create_span:
        parent = MagicMock()
        SpanFactory.create_custom_span(
            kind="custom",
            name="test_custom",
            parent=parent,
            attributes={"key": "value"},
            auto_start=True,
            immediate_export=False
        )
        mock_create_span.assert_called_once_with(
            kind="custom",
            name="test_custom",
            parent=parent,
            attributes={"key": "value"},
            auto_start=True,
            immediate_export=False
        )


def test_auto_register_span_types():
    """Test that the SpanFactory can auto-register span types."""
    # Clear existing registrations
    SpanFactory._span_types = {}
    SpanFactory._initialized = False
    
    # Call auto-register method
    SpanFactory.auto_register_span_types()
    
    # Verify that standard span types are registered
    from agentops.sdk.spans import SessionSpan, AgentSpan, ToolSpan, CustomSpan
    
    assert "session" in SpanFactory._span_types
    assert SpanFactory._span_types["session"] == SessionSpan
    
    assert "agent" in SpanFactory._span_types
    assert SpanFactory._span_types["agent"] == AgentSpan
    
    assert "tool" in SpanFactory._span_types
    assert SpanFactory._span_types["tool"] == ToolSpan
    
    assert "custom" in SpanFactory._span_types
    assert SpanFactory._span_types["custom"] == CustomSpan 