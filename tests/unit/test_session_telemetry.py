"""Tests for session tracing functionality."""

from uuid import uuid4

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter
from opentelemetry.trace import SpanKind

import agentops
from agentops import Config, Session
from agentops.telemetry.session import (SessionTelemetry, _session_tracers,
                                        cleanup_session_tracer,
                                        get_session_tracer,
                                        setup_session_tracer)


def test_session_tracer_initialization(agentops_session):
    """Test that session tracer is properly initialized"""
    setup_session_tracer(agentops_session)

    # Verify tracer was initialized with root span
    assert hasattr(agentops_session, "telemetry")
    assert isinstance(agentops_session.telemetry, SessionTelemetry)
    assert agentops_session.span is not None
    assert agentops_session.span.is_recording()

    # Verify root span has correct attributes
    root_span = agentops_session.span
    assert root_span.attributes["session_id"] == str(agentops_session.session_id)

    # Test new span creation with the active session span
    # Use the actual OpenTelemtry to create a new span
    tracer = trace.get_tracer(__name__)
    child_span = tracer.start_span("test_operation")
    assert child_span.is_recording()
    child_span.set_attribute("test.attribute", "test_value")
    child_span.end()

    # TODO:Verify the span was added to the session
    assert len(list(agentops_session.spans)) == 2
    assert agentops_session.spans[-1] == child_span


def test_session_tracer_cleanup(agentops_session):
    """Test that session tracer is properly cleaned up"""
    # Setup tracer
    setup_session_tracer(agentops_session)
    session_id = str(agentops_session.session_id)

    # Verify tracer exists
    assert session_id in _session_tracers

    # Clean up tracer
    cleanup_session_tracer(agentops_session)

    # Verify tracer was cleaned up
    assert session_id not in _session_tracers, "Tracer not cleaned up"

