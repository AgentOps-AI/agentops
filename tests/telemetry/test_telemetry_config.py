from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
import pytest
from opentelemetry import trace as trace_api
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from unittest.mock import patch

import agentops
from agentops.telemetry.config import OTELConfig
from agentops.config import Configuration
from agentops.telemetry.client import ClientTelemetry


def test_configuration_with_otel():
    """Test that Configuration properly stores OTEL config"""
    exporter = OTLPSpanExporter(endpoint="http://localhost:4317")
    otel_config = OTELConfig(additional_exporters=[exporter])
    
    config = Configuration()
    config.configure(None, telemetry=otel_config)
    
    assert config.telemetry == otel_config
    assert len(config.telemetry.additional_exporters) == 1
    assert isinstance(config.telemetry.additional_exporters[0], OTLPSpanExporter)


def test_init_accepts_telemetry_config():
    """Test that init accepts telemetry configuration"""
    exporter = OTLPSpanExporter(endpoint="http://localhost:4317")
    telemetry = OTELConfig(additional_exporters=[exporter])
    
    agentops.init(
        api_key="test-key",
        telemetry=telemetry
    )
    
    client = agentops.Client()
    assert len(client.telemetry.config.additional_exporters) == 1
    assert isinstance(client.telemetry.config.additional_exporters[0], OTLPSpanExporter)


def test_init_with_env_var_endpoint(monkeypatch, instrumentation):
    """Test initialization with endpoint from environment variable"""
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://custom:4317")
    
    # Create config and client telemetry
    config = OTELConfig()
    telemetry = ClientTelemetry(None)  # Pass None as client for testing
    
    try:
        # Initialize telemetry with our config
        telemetry.initialize(config)
        
        # Check the exporters were configured correctly
        assert config.additional_exporters is None  # Original config should be unchanged
        assert telemetry.config.additional_exporters is not None  # New config should have exporters
        assert len(telemetry.config.additional_exporters) == 1
        
        # Create a test span
        tracer = instrumentation.tracer_provider.get_tracer(__name__)
        with tracer.start_span("test") as span:
            span.set_attribute("test", "value")
        
        # Verify span was captured
        spans = instrumentation.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].name == "test"
        assert spans[0].attributes["test"] == "value"
        
    finally:
        telemetry.shutdown()


@pytest.mark.skip
def test_telemetry_config_overrides_env_vars(instrumentation):
    """Test that explicit telemetry config takes precedence over env vars"""
    custom_exporter = InMemorySpanExporter()
    telemetry_config = OTELConfig(additional_exporters=[custom_exporter])
    
    # Create a mock environment getter that handles default values correctly
    env_vars = {
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://fromenv:4317",
        "OTEL_SERVICE_NAME": "test-service",
        "AGENTOPS_LOGGING_LEVEL": "INFO",  # Add this to handle the logging level check
        "AGENTOPS_API_KEY": None,
        "AGENTOPS_PARENT_KEY": None,
        "AGENTOPS_API_ENDPOINT": None,
        "AGENTOPS_ENV_DATA_OPT_OUT": None
    }
    def mock_env_get(key, default=None):
        return env_vars.get(key, default)
    
    # Need to patch both os.environ.get and os.getenv
    with patch('os.environ.get', side_effect=mock_env_get), \
         patch('os.getenv', side_effect=mock_env_get):
        # Initialize with our custom config
        agentops.init(
            api_key="test-key",
            telemetry=telemetry_config
        )
        
        client = agentops.Client()
        # Verify we're using our custom exporter
        assert len(client.telemetry.config.additional_exporters) == 1
        assert isinstance(client.telemetry.config.additional_exporters[0], InMemorySpanExporter)
        # Verify we're not using the environment variable
        assert not isinstance(client.telemetry.config.additional_exporters[0], OTLPSpanExporter)


def test_multiple_exporters_in_config():
    """Test configuration with multiple exporters"""
    exporter1 = OTLPSpanExporter(endpoint="http://first:4317")
    exporter2 = OTLPSpanExporter(endpoint="http://second:4317")
    
    telemetry = OTELConfig(additional_exporters=[exporter1, exporter2])
    config = Configuration()
    config.configure(None, telemetry=telemetry)
    
    assert len(config.telemetry.additional_exporters) == 2
    assert config.telemetry.additional_exporters == [exporter1, exporter2] 
