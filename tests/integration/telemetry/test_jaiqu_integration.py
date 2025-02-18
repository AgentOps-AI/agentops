"""Integration tests for Jaiqu transformation of OpenTelemetry spans."""

import pytest
import os
from datetime import datetime, timezone
import json
import logging
from agentops.telemetry.jaiqu_transformer import JaiquTransformer
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from agentops.telemetry.postgres_exporter import PostgresSpanExporter
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

@pytest.fixture(scope="module")
def postgres_config():
    """PostgreSQL configuration for testing."""
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "database": os.getenv("POSTGRES_DB", "agentops_test"),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
        "table_name": "otel_spans_test"
    }

@pytest.fixture(scope="module")
def target_schema():
    """Target schema for span transformation."""
    return {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "trace_id": {"type": "string"},
            "parent_id": {"type": "string"},
            "operation": {"type": "string"},
            "service": {"type": "string"},
            "start": {"type": "string", "format": "date-time"},
            "end": {"type": "string", "format": "date-time"},
            "status": {
                "type": "object",
                "properties": {
                    "code": {"type": "integer"},
                    "message": {"type": "string"}
                }
            },
            "attributes": {"type": "object"}
        },
        "required": ["id", "trace_id", "operation", "service", "start", "end"]
    }

@pytest.fixture(scope="module")
def setup_telemetry(postgres_config):
    """Set up OpenTelemetry with PostgreSQL exporter."""
    # Create and configure the tracer provider
    resource = Resource.create({
        SERVICE_NAME: "test_service",
        "environment": "test"
    })
    
    provider = TracerProvider(resource=resource)
    
    # Set up PostgreSQL exporter
    postgres_exporter = PostgresSpanExporter(
        host=postgres_config["host"],
        port=postgres_config["port"],
        database=postgres_config["database"],
        user=postgres_config["user"],
        password=postgres_config["password"],
        table_name=postgres_config["table_name"]
    )
    postgres_processor = BatchSpanProcessor(postgres_exporter)
    provider.add_span_processor(postgres_processor)
    
    # Set as global provider
    trace.set_tracer_provider(provider)
    
    # Get a tracer
    tracer = trace.get_tracer(__name__)
    
    return tracer

@pytest.fixture(scope="module")
def jaiqu_transformer(postgres_config):
    """Create JaiquTransformer instance."""
    return JaiquTransformer(
        host=postgres_config["host"],
        port=postgres_config["port"],
        database=postgres_config["database"],
        user=postgres_config["user"],
        password=postgres_config["password"],
        table_name=postgres_config["table_name"]
    )

def test_end_to_end_transformation(setup_telemetry, jaiqu_transformer, target_schema):
    """Test end-to-end flow from span creation to transformation."""
    tracer = setup_telemetry
    
    # Create a test span
    with tracer.start_as_current_span("test_operation") as span:
        span.set_attribute("custom.attribute", "test_value")
        time.sleep(0.1)  # Ensure some duration
    
    # Wait for BatchSpanProcessor to export
    time.sleep(2)
    
    # Fetch spans from PostgreSQL
    spans = jaiqu_transformer.fetch_spans()
    assert len(spans) > 0
    logging.info(f"Original spans: {json.dumps(spans, indent=2)}")
    
    # Transform spans
    transformed_spans = jaiqu_transformer.transform_spans(spans, target_schema)
    assert len(transformed_spans) > 0
    logging.info(f"Transformed spans: {json.dumps(transformed_spans, indent=2)}")
    
    # Validate first transformed span
    first_span = transformed_spans[0]
    assert "id" in first_span
    assert "trace_id" in first_span
    assert "operation" in first_span
    assert first_span["operation"] == "test_operation"
    assert first_span["service"] == "test_service"
    
    # Validate timestamps
    start_time = datetime.fromisoformat(first_span["start"].replace('Z', '+00:00'))
    end_time = datetime.fromisoformat(first_span["end"].replace('Z', '+00:00'))
    assert start_time < end_time
    assert (end_time - start_time).total_seconds() >= 0.1
    
    # Validate schema
    assert jaiqu_transformer.validate_schema(first_span, target_schema)

def test_span_attribute_preservation(setup_telemetry, jaiqu_transformer, target_schema):
    """Test that span attributes are properly preserved during transformation."""
    tracer = setup_telemetry
    
    test_attributes = {
        "custom.string": "test_value",
        "custom.number": 42,
        "custom.boolean": True
    }
    
    # Create a test span with attributes
    with tracer.start_as_current_span("attribute_test") as span:
        for key, value in test_attributes.items():
            span.set_attribute(key, value)
    
    # Wait for BatchSpanProcessor to export
    time.sleep(2)
    
    # Fetch and transform spans
    spans = jaiqu_transformer.fetch_spans()
    transformed_spans = jaiqu_transformer.transform_spans(spans, target_schema)
    
    # Find our test span
    test_span = next(
        (s for s in transformed_spans if s["operation"] == "attribute_test"),
        None
    )
    assert test_span is not None
    
    # Verify attributes are preserved
    assert "attributes" in test_span
    for key, value in test_attributes.items():
        assert test_span["attributes"][key] == value

def test_error_handling_and_recovery(setup_telemetry, jaiqu_transformer, target_schema):
    """Test error handling and recovery during transformation."""
    tracer = setup_telemetry
    
    # Create multiple spans, including one that might cause issues
    with tracer.start_as_current_span("normal_span") as span1:
        span1.set_attribute("normal", "value")
    
    with tracer.start_as_current_span("problematic_span") as span2:
        # Add some potentially problematic attributes
        span2.set_attribute("binary", b"binary_data")  # Binary data might cause issues
        span2.set_attribute("nested", {"key": "value"})  # Nested dict
    
    # Wait for BatchSpanProcessor to export
    time.sleep(2)
    
    # Fetch and transform spans
    spans = jaiqu_transformer.fetch_spans()
    transformed_spans = jaiqu_transformer.transform_spans(spans, target_schema)
    
    # Verify we got some transformed spans despite potential issues
    assert len(transformed_spans) > 0
    
    # Verify all transformed spans are valid according to schema
    for span in transformed_spans:
        assert jaiqu_transformer.validate_schema(span, target_schema)
