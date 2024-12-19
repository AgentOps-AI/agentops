import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from agentops.session import Session
from agentops.client import Client
from agentops.event import LLMEvent


class BaseProviderTest:
    """Base class for provider tests."""

    async def async_setup_method(self, method):
        """Set up test method."""
        # Initialize mock client and session
        self.mock_req = AsyncMock()
        client = Client()
        client.configure(api_key="test-key")
        config = client._config
        self.session = Session(session_id=uuid4(), config=config)
        self.session.client.http_client = self.mock_req

    async def teardown_method(self, method):
        """Clean up after test."""
        if hasattr(self, 'provider'):
            self.provider.undo_override()

    async def async_verify_events(self, session, expected_count=1):
        """Verify events were recorded."""
        await asyncio.sleep(0.1)  # Allow time for async event processing
        create_events_requests = [req for req in self.mock_req.request_history if req.url.endswith("/v2/create_events")]
        assert len(create_events_requests) >= 1, "No events were recorded"
        request_body = json.loads(create_events_requests[-1].body.decode("utf-8"))
        assert "session_id" in request_body, "Session ID not found in request"

    async def async_verify_llm_event(self, mock_req, model=None):
        """Verify LLM event was recorded."""
        await asyncio.sleep(0.1)  # Allow time for async event processing
        create_events_requests = [req for req in mock_req.request_history if req.url.endswith("/v2/create_events")]
        assert len(create_events_requests) >= 1, "No events were recorded"
        request_body = json.loads(create_events_requests[-1].body.decode("utf-8"))
        assert "event_type" in request_body and request_body["event_type"] == "llms", "LLM event not found"
        if model:
            assert "model" in request_body and request_body["model"] == model, f"Model {model} not found in event"
