import json
import time
from datetime import datetime, timezone
from typing import Dict, Optional, Sequence
from unittest.mock import MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest
import requests_mock
from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExportResult
from opentelemetry.trace import SpanContext, SpanKind, Status, StatusCode
from opentelemetry.trace.span import TraceState

import agentops
from agentops import ActionEvent, Client
from agentops.config import Configuration
from agentops.http_client import HttpClient, HttpStatus, Response
from agentops.session import Session
from agentops.singleton import clear_singletons


def create_mock_response(status_code: int, body: Optional[dict] = None) -> Response:
    """Helper to create mock responses"""
    response = Response()
    response.code = status_code
    response.status = HttpStatus.SUCCESS if status_code == 200 else HttpStatus.INVALID_API_KEY
    response.body = body or {}
    return response


@pytest.fixture
def mock_http_client():
    """Fixture to mock HTTP client responses"""
    with patch("agentops.session.api.HttpClient") as mock:
        # Make sure the mock is also available at module level
        with patch("agentops.http_client.HttpClient", mock):
            yield mock


def test_session_api_batch(mock_http_client):
    """Test batch event sending"""
    session_id = uuid4()
    config = Configuration(api_key="test_key")

    mock_http_client.post.return_value = create_mock_response(200, {"success": True})

    session = Session(session_id=session_id, config=config)
    session.api.batch([])  # Try to send events

    assert mock_http_client.post.called
    assert "events" in mock_http_client.post.call_args[0][1].decode()


def test_session_api_create_session(mock_http_client):
    """Test session creation"""
    session_id = uuid4()
    config = Configuration(api_key="test_key")

    mock_http_client.post.return_value = create_mock_response(
        200, {"success": True, "session_url": f"https://app.agentops.ai/drilldown?session_id={session_id}"}
    )

    session = Session(session_id=session_id, config=config)

    assert mock_http_client.post.called
    payload = json.loads(mock_http_client.post.call_args[0][1].decode())
    assert "session" in payload
    assert payload["session"]["session_id"] == str(session_id)
