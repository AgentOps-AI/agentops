import pytest
from unittest.mock import MagicMock, patch
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

from agentops.telemetry import TelemetryManager
from agentops.session import Session
from agentops.config import Configuration
from agentops.event import LLMEvent

@pytest.fixture
def mock_tracer():
    tracer_provider = TracerProvider()
    processor = BatchSpanProcessor(OTLPSpanExporter())
    tracer_provider.add_span_processor(processor)
    trace.set_tracer_provider(tracer_provider)
    return trace.get_tracer(__name__)

@pytest.fixture
def telemetry_manager():
    return TelemetryManager(
        service_name="agentops_test_service",
        otlp_endpoint="http://localhost:4318/v1/traces",
        enabled=True
    )

def test_telemetry_manager_initialization(telemetry_manager):
    assert telemetry_manager.service_name == "agentops_test_service"
    assert telemetry_manager.otlp_endpoint == "http://localhost:4318/v1/traces"
    assert telemetry_manager.enabled is True

def test_telemetry_manager_disabled():
    manager = TelemetryManager(
        service_name="agentops_test_service",
        otlp_endpoint="http://localhost:4318/v1/traces",
        enabled=False
    )
    assert manager.enabled is False

@pytest.mark.asyncio
async def test_session_telemetry_integration():
    config = Configuration()
    config.enable_telemetry = True
    config.otlp_endpoint = "http://localhost:4318/v1/traces"
    
    session = Session(session_id="test_session", config=config)
    
    # Verify session span creation
    assert hasattr(session, '_session_span')
    assert session._session_span is not None
    
    # Test agent span creation
    agent_id = "test_agent"
    event = LLMEvent(
        agent_id=agent_id,
        prompt="test prompt",
        completion="test completion",
        model="test_model",
        prompt_tokens=10,
        completion_tokens=5,
        cost=0.001
    )
    session.record(event)
    
    # Verify agent context exists
    assert agent_id in session._agent_contexts
    assert session._agent_contexts[agent_id] is not None
    
    # End session and verify cleanup
    session.end_session()
    assert session.telemetry is None
    assert not session.is_running

def test_span_attributes():
    config = Configuration()
    config.enable_telemetry = True
    config.otlp_endpoint = "http://localhost:4318/v1/traces"
    
    session = Session(session_id="test_session", config=config)
    
    # Record an event
    event = LLMEvent(
        agent_id="test_agent",
        prompt="test prompt",
        completion="test completion",
        model="test_model",
        prompt_tokens=10,
        completion_tokens=5,
        cost=0.001
    )
    session.record(event)
    
    # Verify span attributes
    agent_span = trace.get_current_span(session._agent_contexts["test_agent"])
    assert agent_span is not None
    
    # End session
    session.end_session()
    
    # Verify session span attributes
    assert session._session_span.attributes.get("service.name") == "agentops"
    assert session._session_span.attributes.get("session.id") is not None 