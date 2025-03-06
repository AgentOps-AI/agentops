import gc
import uuid
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from agentops.session.tracer import SessionTracer, _session_tracers


def test_session_tracer_global_lifecycle():
    # Create a mock session
    mock_session = MagicMock()
    mock_session.session_id = session_id = str(uuid.uuid4())
    mock_session.dict.return_value = {"session_id": session_id}

    # Verify _session_tracers is empty initially
    assert len(_session_tracers) == 0

    # Mock the BatchSpanProcessor and other dependencies
    with patch("agentops.session.tracer.BatchSpanProcessor") as mock_processor_class, patch(
        "agentops.session.tracer.get_tracer_provider"
    ) as mock_get_provider, patch("agentops.session.tracer.OTLPSpanExporter") as mock_exporter_class, patch(
        "agentops.session.tracer.context"
    ) as mock_context, patch("agentops.session.tracer.trace") as mock_trace:
        # Configure the mocks
        mock_processor_instance = MagicMock()
        mock_processor_class.return_value = mock_processor_instance

        mock_provider = MagicMock()
        mock_get_provider.return_value = mock_provider

        mock_tracer = MagicMock()
        mock_provider.get_tracer.return_value = mock_tracer

        mock_span = MagicMock()
        mock_tracer.start_span.return_value = mock_span

        mock_context_obj = MagicMock()
        mock_trace.set_span_in_context.return_value = mock_context_obj
        mock_context.attach.return_value = "mock-token"

        # Create a session tracer
        tracer = SessionTracer(mock_session)

        # Call start to ensure _session_tracers is updated
        tracer.start()

        # Verify the tracer was added to _session_tracers
        assert len(_session_tracers) == 1
        assert mock_session.session_id in _session_tracers
        assert _session_tracers[mock_session.session_id] is tracer

        # Delete the tracer reference and force garbage collection
        del tracer
        gc.collect()  # Force garbage collection to trigger __del__

        # Verify the tracer was removed from _session_tracers
        assert session_id not in _session_tracers
