"""
Shared fixtures for pytest tests.
"""

import pytest
from unittest.mock import MagicMock, patch

from opentelemetry.trace import Span


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
