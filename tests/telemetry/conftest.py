import uuid
from typing import Generator

import pytest

from agentops.config import Configuration
from agentops.telemetry.exporter import ExportManager
from agentops.telemetry.manager import OTELManager
from agentops.telemetry.metrics import TelemetryMetrics
from agentops.telemetry.processors import EventProcessor


@pytest.fixture
def config() -> Configuration:
    """Provide a test configuration"""
    return Configuration(api_key="test-key")


@pytest.fixture
def session_id() -> uuid.UUID:
    """Provide a test session ID"""
    return uuid.uuid4()


@pytest.fixture
def otel_manager(config: Configuration) -> Generator[OTELManager, None, None]:
    """Provide a configured OTEL manager"""
    manager = OTELManager(config)
    yield manager
    manager.shutdown()


@pytest.fixture
def tracer(otel_manager: OTELManager, session_id: uuid.UUID):
    """Provide a configured tracer"""
    provider = otel_manager.initialize("test-service", str(session_id))
    return otel_manager.get_tracer("test-tracer")


@pytest.fixture
def exporter(session_id: uuid.UUID) -> ExportManager:
    """Provide a configured exporter"""
    return ExportManager(
        session_id=session_id, endpoint="http://localhost:8000/v2/create_events", jwt="test-jwt", api_key="test-key"
    )


@pytest.fixture
def processor(session_id: uuid.UUID, tracer) -> EventProcessor:
    """Provide a configured event processor"""
    return EventProcessor(session_id, tracer)


@pytest.fixture
def metrics() -> Generator[TelemetryMetrics, None, None]:
    """Provide configured metrics"""
    metrics = TelemetryMetrics("test-service")
    yield metrics
    metrics.shutdown()
