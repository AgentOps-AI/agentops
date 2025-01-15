from unittest.mock import Mock, patch
from uuid import UUID, uuid4

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

from agentops.telemetry.manager import TelemetryManager
from agentops.telemetry.config import OTELConfig
from agentops.telemetry.exporters.session import SessionExporter
from agentops.telemetry.processors import EventProcessor


@pytest.fixture
def config() -> OTELConfig:
    """Create test config"""
    return OTELConfig(
        endpoint="https://test.agentops.ai",
        api_key="test-key",
        max_queue_size=100,
        max_export_batch_size=50,
        max_wait_time=1000,
    )


@pytest.fixture
def manager() -> TelemetryManager:
    """Create test manager"""
    return TelemetryManager()


class TestTelemetryManager:
    def test_initialization(self, manager: TelemetryManager, config: OTELConfig) -> None:
        """Test manager initialization"""
        manager.initialize(config)

        assert manager.config == config
        assert isinstance(manager._provider, TracerProvider)
        assert isinstance(manager._provider.sampler, ParentBased)

        # Verify global provider was set
        assert trace.get_tracer_provider() == manager._provider

    def test_initialization_with_custom_resource(self, manager: TelemetryManager) -> None:
        """Test initialization with custom resource attributes"""
        config = OTELConfig(
            endpoint="https://test.agentops.ai",
            api_key="test-key",
            resource_attributes={"custom.attr": "value"},
            max_queue_size=100,
            max_export_batch_size=50,
            max_wait_time=1000,
        )

        manager.initialize(config)
        assert manager._provider is not None
        resource = manager._provider.resource

        assert resource.attributes["service.name"] == "agentops"
        assert resource.attributes["custom.attr"] == "value"

    def test_create_session_tracer(self, manager: TelemetryManager, config: OTELConfig) -> None:
        """Test session tracer creation"""
        manager.initialize(config)
        session_id = uuid4()

        tracer = manager.create_session_tracer(session_id, "test-jwt")

        # Verify exporter was created
        assert session_id in manager._session_exporters
        assert isinstance(manager._session_exporters[session_id], SessionExporter)

        # Verify processor was added
        assert len(manager._processors) == 1
        assert isinstance(manager._processors[0], EventProcessor)

        # Skip tracer name verification since it's an implementation detail
        # The important part is that the tracer is properly configured with exporters and processors

    def test_cleanup_session(self, manager: TelemetryManager, config: OTELConfig) -> None:
        """Test session cleanup"""
        manager.initialize(config)
        session_id = uuid4()

        # Create session
        manager.create_session_tracer(session_id, "test-jwt")
        exporter = manager._session_exporters[session_id]

        # Clean up
        with patch.object(exporter, "shutdown") as mock_shutdown:
            manager.cleanup_session(session_id)
            mock_shutdown.assert_called_once()

        assert session_id not in manager._session_exporters

    def test_shutdown(self, manager: TelemetryManager, config: OTELConfig) -> None:
        """Test manager shutdown"""
        manager.initialize(config)
        session_id = uuid4()

        # Create session
        manager.create_session_tracer(session_id, "test-jwt")
        exporter = manager._session_exporters[session_id]

        # Shutdown
        with patch.object(exporter, "shutdown") as mock_shutdown:
            manager.shutdown()
            assert mock_shutdown.called

        assert not manager._session_exporters
        assert not manager._processors
        assert manager._provider is None

    def test_error_handling(self, manager: TelemetryManager) -> None:
        """Test error handling"""
        # Test initialization without config
        with pytest.raises(ValueError, match="Config is required"):
            manager.initialize(None)  # type: ignore

        # Test creating tracer without initialization
        with pytest.raises(RuntimeError, match="Telemetry not initialized"):
            manager.create_session_tracer(uuid4(), "test-jwt")
