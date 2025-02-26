import pytest

from agentops.telemetry.session import _session_tracers


@pytest.fixture(autouse=True)
def reset_instrumentation():
    """Reset instrumentation state between tests"""
    _session_tracers.clear()
    yield
