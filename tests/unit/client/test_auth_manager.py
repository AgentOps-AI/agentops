"""Tests for the AuthManager class."""

import pytest
import requests
import threading
from unittest import mock

from agentops.client.auth_manager import AuthManager
from agentops.exceptions import AgentOpsApiJwtExpiredException


class TestAuthManager:
    """Tests for the AuthManager class."""

    def test_init(self):
        """Test that the auth manager initializes correctly."""
        auth_manager = AuthManager(token_endpoint="https://api.example.com/auth/token")
        
        # Verify the auth manager was created with the expected parameters
        assert auth_manager.token_endpoint == "https://api.example.com/auth/token"
        assert auth_manager.jwt_token is None
        # Check that _token_lock exists but don't use isinstance
        assert hasattr(auth_manager, "_token_lock")
        assert auth_manager._token_lock is not None

    def test_is_token_valid_with_no_token(self):
        """Test that is_token_valid returns False when no token is set."""
        auth_manager = AuthManager(token_endpoint="https://api.example.com/auth/token")
        
        # Verify is_token_valid returns False
        assert not auth_manager.is_token_valid()

    def test_is_token_valid_with_token(self):
        """Test that is_token_valid returns True when a token is set."""
        auth_manager = AuthManager(token_endpoint="https://api.example.com/auth/token")
        
        # Set a token
        auth_manager.jwt_token = "test-token"
        
        # Verify is_token_valid returns True
        assert auth_manager.is_token_valid()

    def test_get_valid_token_with_no_token(self):
        """Test that get_valid_token fetches a new token when none exists."""
        auth_manager = AuthManager(token_endpoint="https://api.example.com/auth/token")
        
        # Create a mock token fetcher
        token_fetcher = mock.Mock(return_value="new-token")
        
        # Call get_valid_token
        token = auth_manager.get_valid_token("test-api-key", token_fetcher)
        
        # Verify the token fetcher was called
        token_fetcher.assert_called_once_with("test-api-key")
        
        # Verify the token was set and returned
        assert auth_manager.jwt_token == "new-token"
        assert token == "new-token"

    def test_get_valid_token_with_existing_token(self):
        """Test that get_valid_token returns the existing token when one exists."""
        auth_manager = AuthManager(token_endpoint="https://api.example.com/auth/token")
        
        # Set a token
        auth_manager.jwt_token = "existing-token"
        
        # Create a mock token fetcher
        token_fetcher = mock.Mock(return_value="new-token")
        
        # Call get_valid_token
        token = auth_manager.get_valid_token("test-api-key", token_fetcher)
        
        # Verify the token fetcher was not called
        token_fetcher.assert_not_called()
        
        # Verify the existing token was returned
        assert token == "existing-token"

    def test_prepare_auth_headers_with_no_token(self):
        """Test that prepare_auth_headers works with no token."""
        auth_manager = AuthManager(token_endpoint="https://api.example.com/auth/token")
        
        # Call prepare_auth_headers
        headers = auth_manager.prepare_auth_headers("test-api-key")
        
        # Verify the headers
        assert headers["Content-Type"] == "application/json; charset=UTF-8"
        assert headers["Accept"] == "*/*"
        assert headers["X-Agentops-Api-Key"] == "test-api-key"
        assert "Authorization" not in headers

    def test_prepare_auth_headers_with_token(self):
        """Test that prepare_auth_headers works with a token."""
        auth_manager = AuthManager(token_endpoint="https://api.example.com/auth/token")
        
        # Set a token
        auth_manager.jwt_token = "test-token"
        
        # Call prepare_auth_headers
        headers = auth_manager.prepare_auth_headers("test-api-key")
        
        # Verify the headers
        assert headers["Content-Type"] == "application/json; charset=UTF-8"
        assert headers["Accept"] == "*/*"
        assert headers["X-Agentops-Api-Key"] == "test-api-key"
        assert headers["Authorization"] == "Bearer test-token"

    def test_prepare_auth_headers_with_custom_headers(self):
        """Test that prepare_auth_headers works with custom headers."""
        auth_manager = AuthManager(token_endpoint="https://api.example.com/auth/token")
        
        # Set a token
        auth_manager.jwt_token = "test-token"
        
        # Call prepare_auth_headers with custom headers
        headers = auth_manager.prepare_auth_headers(
            "test-api-key",
            custom_headers={
                "X-Custom-Header": "custom-value",
                "Content-Type": "application/xml",  # This will override the default
                "Authorization": "Basic dXNlcjpwYXNz"  # This should be protected
            }
        )
        
        # Verify the headers
        assert headers["Content-Type"] == "application/xml"  # Custom header overrides default
        assert headers["Accept"] == "*/*"
        assert headers["X-Agentops-Api-Key"] == "test-api-key"
        assert headers["Authorization"] == "Bearer test-token"  # Protected header not overridden
        assert headers["X-Custom-Header"] == "custom-value"  # Custom header added

    def test_is_token_expired_response_with_non_error_status(self):
        """Test that is_token_expired_response returns False for non-error status codes."""
        auth_manager = AuthManager(token_endpoint="https://api.example.com/auth/token")
        
        # Create a mock response with a 200 status code
        response = mock.Mock(spec=requests.Response)
        response.status_code = 200
        
        # Verify is_token_expired_response returns False
        assert not auth_manager.is_token_expired_response(response)

    def test_is_token_expired_response_with_error_status_and_expired_token_json(self):
        """Test that is_token_expired_response returns True for error status codes with expired token JSON."""
        auth_manager = AuthManager(token_endpoint="https://api.example.com/auth/token")
        
        # Create a mock response with a 401 status code and expired token JSON
        response = mock.Mock(spec=requests.Response)
        response.status_code = 401
        response.json.return_value = {"error": "Token has expired"}
        
        # Verify is_token_expired_response returns True
        assert auth_manager.is_token_expired_response(response)

    def test_is_token_expired_response_with_error_status_and_token_error_json(self):
        """Test that is_token_expired_response returns True for error status codes with token error JSON."""
        auth_manager = AuthManager(token_endpoint="https://api.example.com/auth/token")
        
        # Create a mock response with a 401 status code and token error JSON
        response = mock.Mock(spec=requests.Response)
        response.status_code = 401
        response.json.return_value = {"error": "Invalid token"}
        
        # Verify is_token_expired_response returns True
        assert auth_manager.is_token_expired_response(response)

    def test_is_token_expired_response_with_error_status_and_non_token_error_json(self):
        """Test that is_token_expired_response returns False for error status codes with non-token error JSON."""
        auth_manager = AuthManager(token_endpoint="https://api.example.com/auth/token")
        
        # Create a mock response with a 401 status code and non-token error JSON
        response = mock.Mock(spec=requests.Response)
        response.status_code = 401
        response.json.return_value = {"error": "Invalid credentials"}
        
        # Verify is_token_expired_response returns False
        assert not auth_manager.is_token_expired_response(response)

    def test_is_token_expired_response_with_error_status_and_expired_token_text(self):
        """Test that is_token_expired_response returns True for error status codes with expired token text."""
        auth_manager = AuthManager(token_endpoint="https://api.example.com/auth/token")
        
        # Create a mock response with a 401 status code and expired token text
        response = mock.Mock(spec=requests.Response)
        response.status_code = 401
        response.json.side_effect = ValueError("Invalid JSON")
        response.text = "Token has expired"
        
        # Verify is_token_expired_response returns True
        assert auth_manager.is_token_expired_response(response)

    def test_is_token_expired_response_with_error_status_and_non_token_error_text(self):
        """Test that is_token_expired_response returns False for error status codes with non-token error text."""
        auth_manager = AuthManager(token_endpoint="https://api.example.com/auth/token")
        
        # Create a mock response with a 401 status code and non-token error text
        response = mock.Mock(spec=requests.Response)
        response.status_code = 401
        response.json.side_effect = ValueError("Invalid JSON")
        response.text = "Invalid credentials"
        
        # Verify is_token_expired_response returns False
        assert not auth_manager.is_token_expired_response(response)

    def test_clear_token(self):
        """Test that clear_token clears the token."""
        auth_manager = AuthManager(token_endpoint="https://api.example.com/auth/token")
        
        # Set a token
        auth_manager.jwt_token = "test-token"
        
        # Call clear_token
        auth_manager.clear_token()
        
        # Verify the token was cleared
        assert auth_manager.jwt_token is None 