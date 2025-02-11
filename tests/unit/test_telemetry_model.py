import pytest
from opentelemetry.trace import Span

from agentops.helpers import get_ISO_time
from agentops.telemetry.model import InstrumentedBase


def test_init_creates_span():
    """Test that initializing InstrumentedBase creates a span"""
    base = InstrumentedBase()
    assert isinstance(base.span, Span)
    assert base.init_timestamp is None
    assert base.end_timestamp is None
    assert not base.is_ended


def test_init_timestamp_setter():
    """Test that setting init_timestamp recreates the span"""
    base = InstrumentedBase()
    original_span_id = base.span.get_span_context().span_id

    timestamp = get_ISO_time()
    base.init_timestamp = timestamp

    assert base.init_timestamp == timestamp
    assert base.span is not None
    new_span_id = base.span.get_span_context().span_id
    assert new_span_id != original_span_id  # Compare span IDs instead of spans


def test_end_timestamp_setter():
    """Test that setting end_timestamp ends the span"""
    base = InstrumentedBase()
    assert base.span is not None

    timestamp = get_ISO_time()
    base.end_timestamp = timestamp

    assert base.end_timestamp == timestamp
    assert base.span is None
    assert base.is_ended


def test_end_method():
    """Test that calling end() sets end_timestamp and ends span"""
    base = InstrumentedBase()
    assert base.span is not None
    assert not base.is_ended

    base.end()

    assert base.end_timestamp is not None
    assert base.span is None
    assert base.is_ended


def test_multiple_end_calls():
    """Test that multiple end() calls don't change the original end_timestamp"""
    base = InstrumentedBase()
    base.end()
    original_end = base.end_timestamp

    base.end()  # Second end() call
    assert base.end_timestamp == original_end


def test_span_readonly():
    """Test that span property is read-only"""
    base = InstrumentedBase()
    with pytest.raises(AttributeError):
        base.span = None


def test_create_span_ends_existing():
    """Test that creating a new span ends any existing span"""
    base = InstrumentedBase()
    original_span_id = base.span.get_span_context().span_id

    base._create_span()  # Create new span

    assert base.span is not None
    new_span_id = base.span.get_span_context().span_id
    assert new_span_id != original_span_id  # Compare span IDs instead of spans
