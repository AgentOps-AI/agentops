import pytest
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import \
    InMemorySpanExporter

import agentops
from agentops.session.tracer import _session_tracers


@pytest.fixture(autouse=True)
def reset_instrumentation():
    """Reset instrumentation state between tests"""
    _session_tracers.clear()
    yield

@pytest.fixture(autouse=True)
def exporter(agentops_config):
    exporter = InMemorySpanExporter()
    agentops_config.exporter = exporter
    yield exporter


@pytest.fixture(autouse=True)
def clear_exporter(exporter):
    exporter.clear()
