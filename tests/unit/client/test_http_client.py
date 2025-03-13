# """Tests for the HttpClient class."""
#
# import pytest
# import requests
# from unittest import mock
# from pytest_mock import MockerFixture
#
# from agentops.client.http.http_client import HttpClient
# from agentops.client.http.http_adapter import AuthenticatedHttpAdapter, BaseHTTPAdapter
# from agentops.client.auth_manager import AuthManager
#
#
# class TestHttpClient:
#     """Tests for the HttpClient class."""
#
#     def test_get_session_creates_new_session_if_none_exists(self):
#         """Test that get_session creates a new session if none exists."""
#         # Reset the session to ensure we're testing from a clean state
#         HttpClient._session = None
#
#         # Call get_session
#         session = HttpClient.get_session()
#
#         # Verify a session was created
#         assert session is not None
#         assert isinstance(session, requests.Session)
#
#         # Verify the session has the expected adapters
#         assert any(isinstance(adapter, BaseHTTPAdapter) for adapter in session.adapters.values())
#
#         # Verify the session has the expected headers
#         assert "Content-Type" in session.headers
#         assert "Connection" in session.headers
#         assert "Keep-Alive" in session.headers
#
#     def test_get_session_returns_existing_session(self):
#         """Test that get_session returns the existing session if one exists."""
#         # Create a session
#         HttpClient._session = None
#         session1 = HttpClient.get_session()
#
#         # Call get_session again
#         session2 = HttpClient.get_session()
#
#         # Verify the same session was returned
#         assert session2 is session1
#
#     def test_get_authenticated_session_creates_new_session(self):
#         """Test that get_authenticated_session creates a new authenticated session."""
#         # Call get_authenticated_session
#         session = HttpClient.get_authenticated_session(
#             endpoint="https://api.example.com",
#             api_key="test-api-key"
#         )
#
#         # Verify a session was created
#         assert session is not None
#         assert isinstance(session, requests.Session)
#
#         # Verify the session has the expected adapters
#         assert any(isinstance(adapter, AuthenticatedHttpAdapter) for adapter in session.adapters.values())
#
#         # Verify the session has the expected headers
#         assert "Content-Type" in session.headers
#         assert "Connection" in session.headers
#         assert "Keep-Alive" in session.headers
#
#     def test_get_authenticated_session_with_custom_token_fetcher(self, mocker: MockerFixture):
#         """Test that get_authenticated_session accepts a custom token fetcher."""
#         # Create a mock token fetcher
#         mock_token_fetcher = mock.Mock(return_value="test-token")
#
#         # Call get_authenticated_session with the custom token fetcher
#         session = HttpClient.get_authenticated_session(
#             endpoint="https://api.example.com",
#             api_key="test-api-key",
#             token_fetcher=mock_token_fetcher
#         )
#
#         # Verify a session was created
#         assert session is not None
#         assert isinstance(session, requests.Session)
#
#         # Get the adapter
#         adapter = next(adapter for adapter in session.adapters.values()
#                       if isinstance(adapter, AuthenticatedHttpAdapter))
#
#         # Verify the adapter has the custom token fetcher
#         assert adapter.token_fetcher is mock_token_fetcher
#
#     def test_request_get(self, mocker: MockerFixture):
#         """Test that request makes a GET request."""
#         # Mock the session
#         mock_session = mock.Mock()
#         mock_get = mock.Mock()
#         mock_session.get = mock_get
#
#         # Mock get_session to return our mock session
#         mocker.patch.object(HttpClient, "get_session", return_value=mock_session)
#
#         # Call request
#         HttpClient.request(
#             method="get",
#             url="https://api.example.com/test",
#             headers={"X-Test": "test"},
#             timeout=10
#         )
#
#         # Verify the session method was called with the expected arguments
#         mock_get.assert_called_once_with(
#             "https://api.example.com/test",
#             headers={"X-Test": "test"},
#             timeout=10,
#             allow_redirects=False
#         )
#
#     def test_request_post(self, mocker: MockerFixture):
#         """Test that request makes a POST request."""
#         # Mock the session
#         mock_session = mock.Mock()
#         mock_post = mock.Mock()
#         mock_session.post = mock_post
#
#         # Mock get_session to return our mock session
#         mocker.patch.object(HttpClient, "get_session", return_value=mock_session)
#
#         # Call request
#         HttpClient.request(
#             method="post",
#             url="https://api.example.com/test",
#             data={"test": "data"},
#             headers={"X-Test": "test"},
#             timeout=10
#         )
#
#         # Verify the session method was called with the expected arguments
#         mock_post.assert_called_once_with(
#             "https://api.example.com/test",
#             json={"test": "data"},
#             headers={"X-Test": "test"},
#             timeout=10,
#             allow_redirects=False
#         )
#
#     def test_request_put(self, mocker: MockerFixture):
#         """Test that request makes a PUT request."""
#         # Mock the session
#         mock_session = mock.Mock()
#         mock_put = mock.Mock()
#         mock_session.put = mock_put
#
#         # Mock get_session to return our mock session
#         mocker.patch.object(HttpClient, "get_session", return_value=mock_session)
#
#         # Call request
#         HttpClient.request(
#             method="put",
#             url="https://api.example.com/test",
#             data={"test": "data"},
#             headers={"X-Test": "test"},
#             timeout=10
#         )
#
#         # Verify the session method was called with the expected arguments
#         mock_put.assert_called_once_with(
#             "https://api.example.com/test",
#             json={"test": "data"},
#             headers={"X-Test": "test"},
#             timeout=10,
#             allow_redirects=False
#         )
#
#     def test_request_delete(self, mocker: MockerFixture):
#         """Test that request makes a DELETE request."""
#         # Mock the session
#         mock_session = mock.Mock()
#         mock_delete = mock.Mock()
#         mock_session.delete = mock_delete
#
#         # Mock get_session to return our mock session
#         mocker.patch.object(HttpClient, "get_session", return_value=mock_session)
#
#         # Call request
#         HttpClient.request(
#             method="delete",
#             url="https://api.example.com/test",
#             headers={"X-Test": "test"},
#             timeout=10
#         )
#
#         # Verify the session method was called with the expected arguments
#         mock_delete.assert_called_once_with(
#             "https://api.example.com/test",
#             headers={"X-Test": "test"},
#             timeout=10,
#             allow_redirects=False
#         )
#
#     def test_request_unsupported_method(self):
#         """Test that request raises an error for unsupported methods."""
#         # Call request with an unsupported method
#         with pytest.raises(ValueError, match="Unsupported HTTP method: patch"):
#             HttpClient.request(
#                 method="patch",
#                 url="https://api.example.com/test"
#             )
