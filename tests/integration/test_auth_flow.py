import pytest
from unittest.mock import patch, MagicMock
from agentops.client import Client
from agentops.exceptions import NoApiKeyException, InvalidApiKeyException, ApiServerException
from agentops.client.api import ApiClient


@pytest.mark.vcr()
def test_auth_flow(mock_api_key):
    """Test the authentication flow using the AgentOps client."""
    with patch("agentops.client.client.ApiClient") as mock_api_client:
        # Create mock API instance
        mock_api = MagicMock()
        mock_api.v3.fetch_auth_token.return_value = {"token": "mock_token", "project_id": "mock_project_id"}
        mock_api_client.return_value = mock_api

        # Initialize the client
        client = Client()
        session = client.init(api_key=mock_api_key)

        # Verify client is initialized
        assert client.initialized
        assert client.api is not None

        # Verify session is created if auto_start_session is True
        if client.config.auto_start_session:
            assert session is not None


@pytest.mark.vcr()
def test_auth_flow_invalid_key():
    """Test authentication flow with invalid API key."""
    with patch("agentops.client.client.ApiClient") as mock_api_client:
        # Create mock API instance that raises an error
        mock_api = MagicMock()
        mock_api.v3.fetch_auth_token.side_effect = ApiServerException("Invalid API key")
        mock_api_client.return_value = mock_api

        client = Client()
        with pytest.raises((InvalidApiKeyException, ApiServerException)) as exc_info:
            client.init(api_key="invalid-key")

        assert "Invalid API key" in str(exc_info.value)


@pytest.mark.vcr()
def test_auth_flow_no_key():
    """Test authentication flow with no API key."""
    client = Client()

    with pytest.raises(NoApiKeyException) as exc_info:
        client.init(api_key=None)

    assert "API Key is missing" in str(exc_info.value)
