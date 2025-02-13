"""Integration tests for the PostgreSQL span exporter.

Tests the OpenTelemetry PostgreSQL exporter implementation, including:
- Basic span export functionality
- Parent-child relationship validation
- Error handling and retries
- Service name consistency
- Connection management
- Invalid span handling
"""

import time
import logging
from unittest.mock import patch, MagicMock

import pytest
import psycopg2
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider, ReadableSpan
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExportResult
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.trace import SpanKind, Status, StatusCode

from agentops.telemetry.postgres_exporter import PostgresSpanExporter

# PostgreSQL connection parameters from docker-compose
POSTGRES_CONN_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "agentops_test",
    "user": "postgres",
    "password": "postgres"
}

# PostgreSQL exporter configuration
POSTGRES_EXPORTER_CONFIG = {
    **POSTGRES_CONN_CONFIG,
    "table_name": "otel_spans"
}

@pytest.fixture(scope="session")
def postgres_connection():
    """Create a connection to PostgreSQL."""
    conn = psycopg2.connect(**POSTGRES_CONN_CONFIG)
    yield conn
    conn.close()

@pytest.fixture(scope="function")
def cleanup_spans(postgres_connection):
    """Clean up spans after each test."""
    yield
    # After each test, clear the spans table
    with postgres_connection.cursor() as cur:
        cur.execute("DELETE FROM otel_spans")
        postgres_connection.commit()

@pytest.fixture(scope="session")
def tracer_provider():
    """Create a TracerProvider with PostgreSQL exporter for testing."""
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME
    
    print("\nSetting up tracer provider...")
    
    # Reset the tracer provider
    trace._TRACER_PROVIDER = None
    
    # Create resource
    resource = Resource.create({
        SERVICE_NAME: "test-service",
        "environment": "test"
    })
    
    # Create provider with resource
    provider = TracerProvider(resource=resource)
    
    # Create and add PostgreSQL exporter
    postgres_exporter = PostgresSpanExporter(**POSTGRES_EXPORTER_CONFIG)
    postgres_processor = BatchSpanProcessor(postgres_exporter)
    provider.add_span_processor(postgres_processor)
    print("Added PostgreSQL span processor")
    
    # Set as global provider
    trace.set_tracer_provider(provider)
    
    return provider



@pytest.mark.timeout(30)
def test_span_export(postgres_connection, tracer_provider, cleanup_spans):
    """Test span export to PostgreSQL."""
    # Get tracer and start root span
    tracer = trace.get_tracer(__name__)
    
    # Create a trace with multiple spans
    with tracer.start_as_current_span(
        name="root_operation",
        kind=SpanKind.SERVER,
        attributes={
            "test.name": "span_export_test",
            "test.type": "integration",
            "custom.attribute": "test_value"
        }
    ) as root_span:
        # Add some child spans
        for i in range(3):
            with tracer.start_as_current_span(
                name=f"child_operation_{i}",
                attributes={"child.index": i}
            ) as child_span:
                # Simulate some work
                time.sleep(0.1)
                child_span.set_status(StatusCode.OK)

    # Wait for spans to be exported and force flush
    time.sleep(5)  # A shorter wait time since we're controlling the spans directly
    
    # Force flush any pending spans
    tracer_provider.force_flush()

    # Verify spans in PostgreSQL
    with postgres_connection.cursor() as cur:
        # Count total spans
        cur.execute("SELECT COUNT(*) FROM otel_spans")
        count = cur.fetchone()[0]
        assert count > 0, "No spans found in PostgreSQL"
        assert count > 0, "No spans were exported to PostgreSQL"

        # Print out all spans and their attributes for debugging

        cur.execute("""
            SELECT service_name, name, attributes, trace_id, span_id, parent_span_id, start_time, end_time
            FROM otel_spans
        """)
        spans = cur.fetchall()
        # Verify spans were returned
        assert len(spans) > 0, "No spans found in database"

        # Check for specific span attributes
        cur.execute("""
            SELECT COUNT(*) FROM otel_spans 
            WHERE service_name = 'test-service' 
            AND attributes->>'test.type' = 'integration'
            AND attributes->>'custom.attribute' = 'test_value'
        """)
        tagged_count = cur.fetchone()[0]
        assert tagged_count == 1, "Root span with expected attributes not found"
        
        # Check child spans
        cur.execute("""
            SELECT COUNT(*) FROM otel_spans 
            WHERE service_name = 'test-service' 
            AND name LIKE 'child_operation_%'
        """)
        child_count = cur.fetchone()[0]
        assert child_count == 3, "Expected 3 child spans"

        # Verify trace hierarchy
        cur.execute("""
            SELECT DISTINCT trace_id, 
                   COUNT(DISTINCT span_id) as span_count,
                   COUNT(DISTINCT parent_span_id) as parent_count
            FROM otel_spans
            GROUP BY trace_id
        """)
        trace_info = cur.fetchone()
        assert trace_info and trace_info[1] > 1, "Expected multiple spans in trace"
        assert trace_info[2] > 0, "Expected parent-child relationships in spans"

@pytest.mark.timeout(30)
def test_retry_on_connection_error(tracer_provider, cleanup_spans):
    """Test that the exporter retries on connection errors."""
    # Create a test span
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("test-retry") as span:
        span.set_attribute("test.retry", "true")
    
    # Mock the connection to fail twice then succeed
    original_connect = psycopg2.connect
    connect_attempts = 0
    
    def mock_connect(*args, **kwargs):
        nonlocal connect_attempts
        connect_attempts += 1
        if connect_attempts <= 2:  # Fail first two attempts
            raise psycopg2.OperationalError("Test connection error")
        return original_connect(*args, **kwargs)
    
    # Patch psycopg2.connect and attempt export
    with patch('psycopg2.connect', side_effect=mock_connect):
        tracer_provider.force_flush()
        time.sleep(1)  # Wait for retry attempts
    
    assert connect_attempts == 3, "Expected 3 connection attempts"

@pytest.mark.timeout(30)
def test_invalid_span_handling(postgres_connection, tracer_provider, cleanup_spans):
    """Test that invalid spans are properly handled and logged."""
    # Create an exporter with a mock logger
    exporter = PostgresSpanExporter(**POSTGRES_EXPORTER_CONFIG)
    mock_logger = MagicMock()
    exporter.logger = mock_logger
    
    # Create an invalid span (missing context)
    invalid_span = MagicMock(spec=ReadableSpan)
    invalid_span.name = "invalid-span"
    invalid_span.context = None
    
    # Export the invalid span
    result = exporter.export([invalid_span])
    
    # Verify the export was successful (skipped invalid span)
    assert result == SpanExportResult.SUCCESS
    
    # Verify error was logged
    mock_logger.error.assert_called_with(
        "Span invalid-span has no context"
    )

@pytest.mark.timeout(30)
def test_service_name_consistency(postgres_connection, tracer_provider, cleanup_spans):
    """Test that service name is consistently set at both resource and span levels."""
    tracer = trace.get_tracer(__name__)
    
    # Create a span with service name in resource
    with tracer.start_as_current_span(
        name="test-service-name",
        kind=SpanKind.SERVER,
        attributes={"custom.attr": "test"}
    ) as span:
        pass
    
    # Force flush and verify in database
    tracer_provider.force_flush()
    time.sleep(1)
    
    with postgres_connection.cursor() as cur:
        cur.execute("""
            SELECT attributes->>'service.name' as span_service_name,
                   service_name as resource_service_name
            FROM otel_spans
            WHERE name = 'test-service-name'
        """)
        result = cur.fetchone()
        
        assert result, "Span not found in database"
        span_service_name, resource_service_name = result
        
        # Verify service name is set at both levels
        assert span_service_name == "test-service"
        assert resource_service_name == "test-service"

@pytest.mark.timeout(30)
def test_span_attributes_completeness(postgres_connection, tracer_provider, cleanup_spans):
    """Test that exported spans have all required attributes."""
    # Get tracer and create a test span
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span(
        name="test-attributes",
        kind=SpanKind.SERVER,
        attributes={
            "test.name": "attributes_test",
            "test.type": "validation"
        }
    ) as test_span:
        # Add some events and status
        test_span.add_event("test_event", {"event.type": "test"})
        test_span.set_status(StatusCode.OK)
        
    # Force flush and wait for export
    provider = tracer_provider
    provider.force_flush()
    time.sleep(1)  # Wait for export
    
    # Check the span in database
    with postgres_connection.cursor() as cur:
        cur.execute("""
            SELECT trace_id, span_id, name, kind, start_time, end_time,
                   status_code, attributes, service_name, resource_attributes
            FROM otel_spans
            WHERE name = 'test-attributes'
            LIMIT 1
        """)
        span = cur.fetchone()
        
        assert span, "No spans found in database"
        assert all(span), "Some required span attributes are null"
        
        # Verify timestamp format
        start_time, end_time = span[4], span[5]
        assert isinstance(start_time, int), "start_time should be an integer"
        assert isinstance(end_time, int), "end_time should be an integer"
        assert end_time >= start_time, "end_time should be >= start_time"
        
        # Verify attributes
        attributes = span[7]  # attributes column
        assert attributes.get("test.name") == "attributes_test", "test.name attribute not found"
        assert attributes.get("test.type") == "validation", "test.type attribute not found"
