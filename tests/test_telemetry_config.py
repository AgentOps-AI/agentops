import pytest
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from unittest.mock import patch

import agentops
from agentops.telemetry.config import OTELConfig
from agentops.config import Configuration


def test_configuration_with_otel():
    """Test that Configuration properly stores OTEL config"""
    exporter = OTLPSpanExporter(endpoint="http://localhost:4317")
    otel_config = OTELConfig(additional_exporters=[exporter])
    
    config = Configuration()
    config.configure(None, otel=otel_config)
    
    assert config.otel == otel_config
    assert config.otel.additional_exporters == [exporter]


def test_init_accepts_telemetry_config():
    """Test that init accepts telemetry configuration"""
    exporter = OTLPSpanExporter(endpoint="http://localhost:4317")
    telemetry = OTELConfig(additional_exporters=[exporter])
    
    agentops.init(
        api_key="test-key",
        telemetry=telemetry
    )
    
    # Verify exporter was configured
    client = agentops.Client()
    assert client.telemetry.config.additional_exporters == [exporter]


def test_init_with_env_var_endpoint():
    """Test configuring exporter endpoint via env var"""
    with patch('os.environ.get') as mock_env:
        mock_env.return_value = "http://custom:4317"
        
        agentops.init(api_key="test-key")
        
        client = agentops.Client()
        assert client.telemetry.config is not None
        
        # Should have created an OTLPSpanExporter with the env var endpoint
        exporters = client.telemetry.config.additional_exporters
        assert len(exporters) == 1
        assert isinstance(exporters[0], OTLPSpanExporter)
        assert exporters[0].endpoint == "http://custom:4317"


def test_telemetry_config_overrides_env_vars():
    """Test that explicit telemetry config takes precedence over env vars"""
    custom_exporter = OTLPSpanExporter(endpoint="http://explicit:4317")
    telemetry = OTELConfig(additional_exporters=[custom_exporter])
    
    with patch('os.environ.get') as mock_env:
        mock_env.return_value = "http://fromenv:4317"
        
        agentops.init(
            api_key="test-key",
            telemetry=telemetry
        )
        
        client = agentops.Client()
        assert client.telemetry.config.additional_exporters == [custom_exporter]


def test_multiple_exporters_in_config():
    """Test configuration with multiple exporters"""
    exporter1 = OTLPSpanExporter(endpoint="http://first:4317")
    exporter2 = OTLPSpanExporter(endpoint="http://second:4317")
    
    telemetry = OTELConfig(additional_exporters=[exporter1, exporter2])
    config = Configuration()
    config.configure(None, otel=telemetry)
    
    assert len(config.otel.additional_exporters) == 2
    assert config.otel.additional_exporters == [exporter1, exporter2] 