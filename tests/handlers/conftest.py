"""Test fixtures for integrations."""

import os
import re
import uuid
from collections import defaultdict
from unittest import mock

import pytest
import requests_mock
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider, ReadableSpan
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.trace import Status, StatusCode, SpanKind

import agentops
from agentops.config import Config
from tests.fixtures.client import *  # noqa
from tests.unit.sdk.instrumentation_tester import InstrumentationTester


@pytest.fixture
def api_key() -> str:
    """Standard API key for testing"""
    return "test-api-key"


@pytest.fixture
def endpoint() -> str:
    """Base API URL"""
    return Config().endpoint


@pytest.fixture(autouse=True)
def mock_req(endpoint, api_key):
    """
    Mocks AgentOps backend API requests.
    """
    with requests_mock.Mocker(real_http=False) as m:
        # Map session IDs to their JWTs
        m.post(endpoint + "/v3/auth/token", json={"token": str(uuid.uuid4()),
               "project_id": "test-project-id", "api_key": api_key})
        yield m


@pytest.fixture
def noinstrument():
    # Tells the client to not instrument LLM calls
    yield


@pytest.fixture
def mock_config(mocker):
    """Mock the Client.configure method"""
    return mocker.patch("agentops.client.Client.configure")


@pytest.fixture
def instrumentation():
    """Fixture for the instrumentation tester."""
    tester = InstrumentationTester()
    yield tester
    tester.reset()


@pytest.fixture
def tracer_provider():
    """Create a tracer provider with memory exporter for testing."""
    provider = TracerProvider()
    exporter = InMemorySpanExporter()
    processor = SimpleSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    return provider, exporter


@pytest.fixture
def mock_span():
    """Create a mock span for testing."""
    span = mock.Mock(spec=ReadableSpan)
    span.name = "test_span"
    span.kind = SpanKind.INTERNAL
    span.attributes = {}
    span.status = Status(StatusCode.OK)
    span.parent = None
    span.context = mock.Mock()
    span.context.trace_id = 0x1234567890abcdef1234567890abcdef
    span.context.span_id = 0x1234567890abcdef
    return span


@pytest.fixture
def test_run_ids():
    """Create test run IDs for callback testing."""
    return {
        "run_id": uuid.uuid4(),
        "parent_run_id": uuid.uuid4(),
    }


@pytest.fixture
def test_llm_inputs():
    """Create test LLM inputs for callback testing."""
    return {
        "serialized": {"name": "test-model"},
        "prompts": ["test prompt"],
        "metadata": {"test": "metadata"},
    }


@pytest.fixture
def test_chain_inputs():
    """Create test chain inputs for callback testing."""
    return {
        "serialized": {"name": "test-chain"},
        "inputs": {"test": "input"},
    }


@pytest.fixture
def test_tool_inputs():
    """Create test tool inputs for callback testing."""
    return {
        "serialized": {"name": "test-tool"},
        "input_str": "test input",
    }


@pytest.fixture
def test_agent_inputs():
    """Create test agent inputs for callback testing."""
    return {
        "action": mock.Mock(
            tool="test-tool",
            tool_input="test input",
            log="test log",
        ),
        "finish": mock.Mock(
            return_values={"output": "test output"},
            log="test log",
        ),
    }


@pytest.fixture
def test_retry_state():
    """Create test retry state for callback testing."""
    return type("RetryState", (), {
        "attempt_number": 2,
        "outcome": type("Outcome", (), {
            "exception": lambda: Exception("test retry error"),
        })(),
    })() 