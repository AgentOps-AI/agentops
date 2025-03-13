import sys
import os
import pytest
from unittest.mock import patch, MagicMock

from opentelemetry import trace
from opentelemetry.trace import Span

# Import directly from the module file to avoid circular imports
from agentops.sdk.decorators.context_utils import use_span_context, with_span_context, get_trace_id


@pytest.fixture
def mock_span():
    """Fixture to create a mock span with a trace ID."""
    span = MagicMock(spec=Span)
    span.get_span_context.return_value.trace_id = 123456789
    return span


@pytest.fixture
def mock_context_deps():
    """Fixture to mock the context dependencies."""
    with (
        patch("agentops.sdk.decorators.context_utils.context") as mock_context,
        patch("agentops.sdk.decorators.context_utils.trace") as mock_trace,
        patch("agentops.sdk.decorators.context_utils.logger") as mock_logger,
    ):
        # Set up the mocks
        mock_context.get_current.return_value = "current_context"
        mock_trace.set_span_in_context.return_value = "new_context"
        mock_context.attach.return_value = "token"

        yield {"context": mock_context, "trace": mock_trace, "logger": mock_logger}


def test_use_span_context(mock_span, mock_context_deps):
    """Test that the use_span_context context manager works correctly."""
    mock_context = mock_context_deps["context"]
    mock_trace = mock_context_deps["trace"]
    mock_logger = mock_context_deps["logger"]

    # Use the context manager
    with use_span_context(mock_span):
        # Verify the context was attached
        mock_context.get_current.assert_called_once()
        mock_trace.set_span_in_context.assert_called_once_with(mock_span, "current_context")
        mock_context.attach.assert_called_once_with("new_context")
        mock_logger.debug.assert_called_with("Span context attached: 123456789")

    # Verify the context was detached
    mock_context.detach.assert_called_once_with("token")
    mock_logger.debug.assert_called_with("Span context detached: 123456789")


def test_get_trace_id(mock_span):
    """Test that get_trace_id returns the correct trace ID."""
    # Get the trace ID
    trace_id = get_trace_id(mock_span)

    # Verify the trace ID
    assert trace_id == "123456789"

    # Test with None span
    trace_id = get_trace_id(None)
    assert trace_id == "unknown"


def test_with_span_context(mock_span, mock_context_deps):
    """Test that the with_span_context decorator works correctly."""
    mock_context = mock_context_deps["context"]
    mock_trace = mock_context_deps["trace"]
    mock_logger = mock_context_deps["logger"]

    # Create a class with a span attribute
    class TestClass:
        def __init__(self):
            self.span = mock_span

        @with_span_context
        def test_method(self):
            return "test"

    # Create an instance
    test_instance = TestClass()

    # Call the decorated method
    result = test_instance.test_method()

    # Verify the result
    assert result == "test"

    # Verify the context was attached and detached
    mock_context.get_current.assert_called_once()
    mock_trace.set_span_in_context.assert_called_once_with(test_instance.span, "current_context")
    mock_context.attach.assert_called_once_with("new_context")
    mock_context.detach.assert_called_once_with("token")
