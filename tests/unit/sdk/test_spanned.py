import pytest
from unittest.mock import MagicMock, patch
from uuid import UUID

from opentelemetry.trace import StatusCode

from agentops.sdk.spanned import SpannedBase


# Create a concrete implementation of SpannedBase for testing
class TestSpan(SpannedBase):
    """Concrete implementation of SpannedBase for testing."""
    pass


def test_init():
    """Test initialization."""
    # Test basic initialization
    span = TestSpan(name="test", kind="test")
    assert span.name == "test"
    assert span.kind == "test"
    assert span._parent is None
    assert not span.immediate_export
    assert not span.is_started
    assert not span.is_ended
    
    # Test with immediate_export
    span = TestSpan(name="test", kind="test", immediate_export=True)
    assert span.immediate_export
    assert span._attributes["export.immediate"] == True


@patch("agentops.sdk.spanned.trace")
def test_start(mock_trace):
    """Test starting a span."""
    # Set up mocks
    mock_tracer = MagicMock()
    mock_trace.get_tracer.return_value = mock_tracer
    mock_span = MagicMock()
    mock_tracer.start_span.return_value = mock_span
    mock_context = MagicMock()
    mock_trace.set_span_in_context.return_value = mock_context
    
    # Test starting a span
    span = TestSpan(name="test", kind="test")
    result = span.start()
    
    # Verify
    assert result == span
    assert span.is_started
    assert not span.is_ended
    assert span.start_time is not None
    assert span.end_time is None
    mock_trace.get_tracer.assert_called_once_with("agentops")
    mock_tracer.start_span.assert_called_once()
    mock_trace.set_span_in_context.assert_called_once_with(mock_span)
    
    # Test starting an already started span
    mock_trace.reset_mock()
    mock_tracer.reset_mock()
    result = span.start()
    assert result == span
    mock_trace.get_tracer.assert_not_called()
    mock_tracer.start_span.assert_not_called()


def test_end():
    """Test ending a span."""
    # Set up
    span = TestSpan(name="test", kind="test")
    mock_span = MagicMock()
    span._span = mock_span
    span._is_started = True
    
    # Test ending a span
    result = span.end()
    
    # Verify
    assert result == span
    assert span.is_started
    assert span.is_ended
    assert span.end_time is not None
    mock_span.end.assert_called_once()
    
    # Test ending an already ended span
    mock_span.reset_mock()
    result = span.end()
    assert result == span
    mock_span.end.assert_not_called()


def test_update():
    """Test updating a span."""
    # Set up
    span = TestSpan(name="test", kind="test", immediate_export=True)
    mock_span = MagicMock()
    span._span = mock_span
    span._is_started = True
    
    # Test updating a span
    result = span.update()
    
    # Verify
    assert result == span
    mock_span.set_attribute.assert_called_once()
    assert "export.update" in mock_span.set_attribute.call_args[0]
    
    # Test updating a span that's not configured for immediate export
    mock_span.reset_mock()
    span._immediate_export = False
    result = span.update()
    assert result == span
    mock_span.set_attribute.assert_not_called()
    
    # Test updating a span that's not started
    mock_span.reset_mock()
    span._immediate_export = True
    span._is_started = False
    result = span.update()
    assert result == span
    mock_span.set_attribute.assert_not_called()
    
    # Test updating a span that's ended
    mock_span.reset_mock()
    span._is_started = True
    span._is_ended = True
    result = span.update()
    assert result == span
    mock_span.set_attribute.assert_not_called()


def test_context_manager():
    """Test using a span as a context manager."""
    # Set up
    span = TestSpan(name="test", kind="test")
    span.start = MagicMock(return_value=span)
    span.end = MagicMock(return_value=span)
    
    # Test normal execution
    with span as s:
        assert s == span
    span.start.assert_called_once()
    span.end.assert_called_once_with(StatusCode.OK)
    
    # Test with exception
    span.start.reset_mock()
    span.end.reset_mock()
    try:
        with span as s:
            raise ValueError("Test error")
    except ValueError:
        pass
    span.start.assert_called_once()
    span.end.assert_called_once()
    assert span.end.call_args[0][0] == StatusCode.ERROR


def test_to_dict():
    """Test converting a span to a dictionary."""
    # Set up
    span = TestSpan(name="test", kind="test", immediate_export=True)
    span._is_started = True
    span._start_time = "2023-01-01T00:00:00Z"
    
    # Test
    result = span.to_dict()
    
    # Verify
    assert result["name"] == "test"
    assert result["kind"] == "test"
    assert result["start_time"] == "2023-01-01T00:00:00Z"
    assert result["end_time"] is None
    assert result["is_started"]
    assert not result["is_ended"]
    assert result["immediate_export"] 