"""Tests for the HTTP adapter classes."""

from urllib3.util import Retry

from agentops.client.http.http_adapter import BaseHTTPAdapter

# from agentops.client.auth_manager import AuthManager


class TestBaseHTTPAdapter:
    """Tests for the BaseHTTPAdapter class."""

    def test_init_with_default_params(self):
        """Test that the adapter initializes with default parameters."""
        adapter = BaseHTTPAdapter()

        # Verify the adapter was created with the expected parameters
        assert adapter.poolmanager is not None

        # Check that max_retries was set
        assert adapter.max_retries is not None
        assert isinstance(adapter.max_retries, Retry)
        assert adapter.max_retries.total == 3
        assert adapter.max_retries.backoff_factor == 0.1
        assert adapter.max_retries.status_forcelist == [500, 502, 503, 504]

    def test_init_with_custom_params(self):
        """Test that the adapter initializes with custom parameters."""
        custom_retry = Retry(total=5, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])

        adapter = BaseHTTPAdapter(pool_connections=20, pool_maxsize=300, max_retries=custom_retry)

        # Verify the adapter was created with the expected parameters
        assert adapter.poolmanager is not None

        # Check that max_retries was set to our custom value
        assert adapter.max_retries is custom_retry
        assert adapter.max_retries.total == 5
        assert adapter.max_retries.backoff_factor == 0.5
        assert adapter.max_retries.status_forcelist == [429, 500, 502, 503, 504]


# class TestAuthenticatedHttpAdapter:
#     """Tests for the AuthenticatedHttpAdapter class."""
#
#     @pytest.fixture
#     def auth_manager(self):
#         """Create an AuthManager for testing."""
#         return AuthManager(token_endpoint="https://api.example.com/auth/token")
#
#     @pytest.fixture
#     def token_fetcher(self):
#         """Create a token fetcher function for testing."""
#         return mock.Mock(return_value={"token": "test-token", "project_id": "test-project"})
#
#     def test_init(self, auth_manager, token_fetcher):
#         """Test that the adapter initializes correctly."""
#         adapter = AuthenticatedHttpAdapter(
#             auth_manager=auth_manager,
#             api_key="test-api-key",
#             token_fetcher=token_fetcher
#         )
#
#         # Verify the adapter was created with the expected parameters
#         assert adapter.auth_manager is auth_manager
#         assert adapter.api_key == "test-api-key"
#         assert adapter.token_fetcher is token_fetcher
#
#         # Verify it's a subclass of BaseHTTPAdapter
#         assert isinstance(adapter, BaseHTTPAdapter)
#
#     def test_add_headers(self, auth_manager, token_fetcher):
#         """Test that add_headers adds authentication headers to the request."""
#         # Setup
#         adapter = AuthenticatedHttpAdapter(
#             auth_manager=auth_manager,
#             api_key="test-api-key",
#             token_fetcher=token_fetcher
#         )
#
#         # Mock the auth manager methods
#         auth_manager.maybe_fetch = mock.Mock(return_value={"token": "test-token", "project_id": "test-project"})
#         auth_manager.prepare_auth_headers = mock.Mock(return_value={
#             "Authorization": "Bearer test-token",
#             "Content-Type": "application/json; charset=UTF-8",
#             "X-Agentops-Api-Key": "test-api-key"
#         })
#
#         # Create a request
#         request = requests.Request('GET', 'https://api.example.com/test').prepare()
#
#         # Call add_headers
#         modified_request = adapter.add_headers(request)
#
#         # Verify the auth manager methods were called
#         auth_manager.maybe_fetch.assert_called_once_with("test-api-key", token_fetcher)
#         auth_manager.prepare_auth_headers.assert_called_once_with("test-api-key")
#
#         # Verify the headers were added to the request
#         assert modified_request.headers["Authorization"] == "Bearer test-token"
#         assert modified_request.headers["Content-Type"] == "application/json; charset=UTF-8"
#         assert modified_request.headers["X-Agentops-Api-Key"] == "test-api-key"
#
#     def test_send_success(self, auth_manager, token_fetcher, mocker: MockerFixture):
#         """Test that send successfully sends a request."""
#         # Setup
#         adapter = AuthenticatedHttpAdapter(
#             auth_manager=auth_manager,
#             api_key="test-api-key",
#             token_fetcher=token_fetcher
#         )
#
#         # Mock the add_headers method
#         mocker.patch.object(adapter, 'add_headers', side_effect=lambda r, **kw: r)
#
#         # Mock the parent send method
#         mock_response = mock.Mock(spec=requests.Response)
#         mock_response.status_code = 200
#         mocker.patch.object(BaseHTTPAdapter, 'send', return_value=mock_response)
#
#         # Mock the is_token_expired_response method
#         auth_manager.is_token_expired_response = mock.Mock(return_value=False)
#
#         # Create a request
#         request = requests.Request('GET', 'https://api.example.com/test').prepare()
#
#         # Call send
#         response = adapter.send(request)
#
#         # Verify the response
#         assert response is mock_response
#         assert response.status_code == 200
#
#         # Verify the methods were called
#         adapter.add_headers.assert_called_once()
#         BaseHTTPAdapter.send.assert_called_once()
#         auth_manager.is_token_expired_response.assert_called_once_with(mock_response)
#
#     def test_send_with_token_refresh(self, auth_manager, token_fetcher, mocker: MockerFixture):
#         """Test that send refreshes the token if it's expired."""
#         # Setup
#         adapter = AuthenticatedHttpAdapter(
#             auth_manager=auth_manager,
#             api_key="test-api-key",
#             token_fetcher=token_fetcher
#         )
#
#         # Mock the add_headers method
#         mocker.patch.object(adapter, 'add_headers', side_effect=lambda r, **kw: r)
#
#         # Mock the parent send method to return a 401 response first, then a 200 response
#         expired_response = mock.Mock(spec=requests.Response)
#         expired_response.status_code = 401
#
#         success_response = mock.Mock(spec=requests.Response)
#         success_response.status_code = 200
#
#         mocker.patch.object(
#             BaseHTTPAdapter,
#             'send',
#             side_effect=[expired_response, success_response]
#         )
#
#         # Mock the auth manager methods
#         auth_manager.is_token_expired_response = mock.Mock(return_value=True)
#         auth_manager.clear_token = mock.Mock()
#         auth_manager.maybe_fetch = mock.Mock(return_value={"token": "new-token", "project_id": "test-project"})
#
#         # Create a request
#         request = requests.Request('GET', 'https://api.example.com/test').prepare()
#
#         # Call send
#         response = adapter.send(request)
#
#         # Verify the auth manager methods were called
#         auth_manager.is_token_expired_response.assert_called_once_with(expired_response)
#         auth_manager.clear_token.assert_called_once()
#         auth_manager.maybe_fetch.assert_called_once_with("test-api-key", token_fetcher)
#
#         # Verify the response is the success response
#         assert response is success_response
#
#     def test_send_with_token_refresh_failure(self, auth_manager, token_fetcher, mocker: MockerFixture):
#         """Test that send handles token refresh failures gracefully."""
#         # Setup
#         adapter = AuthenticatedHttpAdapter(
#             auth_manager=auth_manager,
#             api_key="test-api-key",
#             token_fetcher=token_fetcher
#         )
#
#         # Mock the add_headers method
#         mocker.patch.object(adapter, 'add_headers', side_effect=lambda r, **kw: r)
#
#         # Mock the parent send method to return a 401 response
#         expired_response = mock.Mock(spec=requests.Response)
#         expired_response.status_code = 401
#
#         mocker.patch.object(BaseHTTPAdapter, 'send', return_value=expired_response)
#
#         # Mock the auth manager methods
#         auth_manager.is_token_expired_response = mock.Mock(return_value=True)
#         auth_manager.clear_token = mock.Mock()
#         auth_manager.maybe_fetch = mock.Mock(side_effect=AgentOpsApiJwtExpiredException("Failed to refresh token"))
#
#         # Create a request
#         request = requests.Request('GET', 'https://api.example.com/test').prepare()
#
#         # Call send
#         response = adapter.send(request)
#
#         # Verify the response is the original 401 response
#         assert response is expired_response
#         assert response.status_code == 401
#
#         # Verify the methods were called
#         adapter.add_headers.assert_called_once()  # Only called for initial request
#         BaseHTTPAdapter.send.assert_called_once()  # Only called for initial request
#         auth_manager.is_token_expired_response.assert_called_once_with(expired_response)
#         auth_manager.clear_token.assert_called_once()
#         auth_manager.maybe_fetch.assert_called_once_with("test-api-key", token_fetcher)
