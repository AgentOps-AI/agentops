import gc
import uuid
from unittest.mock import MagicMock

import pytest

from agentops.session.tracer import SessionTracer, _session_tracers


def test_session_tracer_global_lifecycle():
    # Create a mock session
    mock_session = MagicMock()

    mock_session.session_id = session_id = str(uuid.uuid4())

    # Verify _session_tracers is empty initially
    assert len(_session_tracers) == 0
    # Create a session tracer
    tracer = SessionTracer(mock_session)

    # Verify the tracer was added to _session_tracers
    assert len(_session_tracers) == 1
    assert mock_session.session_id in _session_tracers
    assert _session_tracers[mock_session.session_id] is tracer
    
    # Store the session_id before deleting the tracer
    
    # Delete the tracer reference and force garbage collection
    del tracer
    gc.collect()  # Force garbage collection to trigger __del__
    # Verify _session_tracers is empty again
    assert len(_session_tracers) == 0
    assert session_id not in _session_tracers
