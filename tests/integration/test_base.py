import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from agentops.session import Session
from agentops.client import Client
from agentops.http_client import HttpClient
from agentops.event import LLMEvent


class BaseProviderTest:
    """Base class for provider tests."""

    async def async_setup_method(self, method):
        """Set up test method."""
        # Initialize request history tracking
        self.request_history = []

        # Mock successful event recording response
        async def mock_post(url, data=None, *args, **kwargs):
            mock_response = MagicMock()
            mock_response.code = 200
            mock_response.status = 200
            mock_response.json.return_value = {"status": "success"}

            # Store request details for verification
            request_data = {
                'url': url,
                'json': json.loads(data.decode('utf-8')) if data else {},
                'method': 'POST'
            }
            self.request_history.append(request_data)
            return mock_response

        # Patch HttpClient.post to use our mock
        self.http_client_patcher = patch.object(HttpClient, 'post', side_effect=mock_post)
        self.mock_http_client = self.http_client_patcher.start()

        # Configure client and session
        client = Client()
        client.configure(api_key="test-key")
        config = client._config
        self.session = Session(session_id=uuid4(), config=config)

    async def teardown_method(self, method):
        """Clean up after test."""
        if hasattr(self, "provider"):
            self.provider.undo_override()
        if hasattr(self, 'http_client_patcher'):
            self.http_client_patcher.stop()

    async def async_verify_events(self, session, expected_count=1):
        """Verify events were recorded."""
        await asyncio.sleep(0.1)  # Allow time for async event processing
        create_events_requests = [
            req for req in self.request_history
            if isinstance(req['url'], str) and req['url'].endswith("/v2/create_events")
        ]
        assert len(create_events_requests) >= expected_count, f"Expected at least {expected_count} event(s), but no events were recorded"
        return create_events_requests

    async def async_verify_llm_event(self, mock_req, model=None):
        """Verify LLM event was recorded."""
        await asyncio.sleep(0.1)  # Allow time for async event processing
        create_events_requests = [
            req for req in self.request_history
            if isinstance(req['url'], str) and req['url'].endswith("/v2/create_events")
        ]
        assert len(create_events_requests) >= 1, "No events were recorded"
        if model:
            event_data = create_events_requests[0]['json']['events'][0]
            assert event_data.get("model") == model, f"Expected model {model}, got {event_data.get('model')}"
        return create_events_requests
