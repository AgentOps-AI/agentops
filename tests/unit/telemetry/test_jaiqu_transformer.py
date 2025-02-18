"""Unit tests for the JaiquTransformer."""

import pytest
from datetime import datetime, timezone
import json
from agentops.telemetry.jaiqu_transformer import JaiquTransformer
import psycopg2
from unittest.mock import MagicMock, patch

@pytest.fixture
def sample_span_data():
    """Sample OpenTelemetry span data."""
    return {
        "trace_id": "0123456789abcdef0123456789abcdef",
        "span_id": "0123456789abcdef",
        "parent_span_id": "fedcba9876543210",
        "name": "test_span",
        "kind": 1,  # SERVER
        "start_time": 1645567489000000000,  # nanoseconds
        "end_time": 1645567490000000000,
        "attributes": {
            "service.name": "test_service",
            "custom.attribute": "test_value"
        },
        "status": {
            "status_code": 1,  # OK
            "description": "Success"
        }
    }

@pytest.fixture
def sample_target_schema():
    """Sample target schema for transformation."""
    return {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "operation": {"type": "string"},
            "service": {"type": "string"},
            "start": {"type": "string", "format": "date-time"},
            "end": {"type": "string", "format": "date-time"},
            "metadata": {"type": "object"}
        },
        "required": ["id", "operation", "service", "start", "end"]
    }

@pytest.fixture
def transformer():
    """Create a JaiquTransformer instance."""
    return JaiquTransformer()

def test_init_transformer():
    """Test JaiquTransformer initialization."""
    transformer = JaiquTransformer(
        host="testhost",
        port=5433,
        database="testdb",
        user="testuser",
        password="testpass",
        table_name="test_table"
    )
    
    assert transformer.connection_params["host"] == "testhost"
    assert transformer.connection_params["port"] == 5433
    assert transformer.connection_params["database"] == "testdb"
    assert transformer.connection_params["user"] == "testuser"
    assert transformer.connection_params["password"] == "testpass"
    assert transformer.table_name == "test_table"

@patch('psycopg2.connect')
def test_fetch_spans(mock_connect, transformer, sample_span_data):
    """Test fetching spans from PostgreSQL."""
    # Mock cursor and connection
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [(json.dumps(sample_span_data),)]
    
    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
    mock_connect.return_value = mock_conn
    
    # Test fetching all spans
    spans = transformer.fetch_spans()
    assert len(spans) == 1
    assert spans[0] == json.dumps(sample_span_data)
    
    # Test fetching spans with trace_id
    spans = transformer.fetch_spans(trace_id="test_trace")
    assert len(spans) == 1
    assert spans[0] == json.dumps(sample_span_data)

def test_transform_span(transformer, sample_span_data, sample_target_schema):
    """Test transforming a single span."""
    transformed = transformer.transform_span(sample_span_data, sample_target_schema)
    
    # Verify basic structure
    assert "id" in transformed
    assert "operation" in transformed
    assert "service" in transformed
    assert "start" in transformed
    assert "end" in transformed
    
    # Verify timestamps are in ISO format
    start_time = datetime.fromisoformat(transformed["start"].replace('Z', '+00:00'))
    end_time = datetime.fromisoformat(transformed["end"].replace('Z', '+00:00'))
    assert start_time.tzinfo == timezone.utc
    assert end_time.tzinfo == timezone.utc

def test_transform_spans(transformer, sample_span_data, sample_target_schema):
    """Test transforming multiple spans."""
    spans = [sample_span_data, sample_span_data]
    transformed = transformer.transform_spans(spans, sample_target_schema)
    
    assert len(transformed) == 2
    for span in transformed:
        assert "id" in span
        assert "operation" in span
        assert "service" in span
        assert "start" in span
        assert "end" in span

def test_validate_schema(transformer, sample_target_schema):
    """Test schema validation."""
    valid_data = {
        "id": "test_id",
        "operation": "test_operation",
        "service": "test_service",
        "start": "2024-02-19T00:00:00Z",
        "end": "2024-02-19T00:01:00Z",
        "metadata": {"key": "value"}
    }
    
    invalid_data = {
        "id": "test_id",
        # Missing required fields
        "metadata": {"key": "value"}
    }
    
    assert transformer.validate_schema(valid_data, sample_target_schema) is True
    assert transformer.validate_schema(invalid_data, sample_target_schema) is False

def test_error_handling(transformer, sample_span_data, sample_target_schema):
    """Test error handling in transformation."""
    # Test missing required fields
    invalid_span = {"invalid": "data"}
    with pytest.raises(ValueError, match="Missing required field: span_id"):
        transformer.transform_span(invalid_span, sample_target_schema)
    
    # Test missing timestamps
    invalid_span = {"span_id": "test", "name": "test"}
    with pytest.raises(ValueError, match="Missing required fields: start_time or end_time"):
        transformer.transform_span(invalid_span, sample_target_schema)
    
    # Test invalid timestamp format
    invalid_span = {
        "span_id": "test",
        "name": "test",
        "start_time": "invalid",
        "end_time": "invalid"
    }
    with pytest.raises(ValueError, match="Invalid timestamp format"):
        transformer.transform_span(invalid_span, sample_target_schema)
