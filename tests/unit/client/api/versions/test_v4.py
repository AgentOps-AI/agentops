import pytest
from unittest.mock import Mock, patch
from requests.models import Response

from agentops.client.api.versions.v4 import V4Client
from agentops.exceptions import ApiServerException


class TestV4Client:
    def setup_method(self):
        """Set up test fixtures."""
        self.client = V4Client("https://api.agentops.com")
        self.client.auth_token = "test_token"

    def test_set_auth_token(self):
        """Test setting the authentication token."""
        client = V4Client("https://api.agentops.com")
        client.set_auth_token("new_token")
        assert client.auth_token == "new_token"

    def test_prepare_headers_without_custom_headers(self):
        """Test preparing headers without custom headers."""
        with patch("agentops.client.api.versions.v4.get_agentops_version", return_value="1.2.3"):
            headers = self.client.prepare_headers()

            assert headers["Authorization"] == "Bearer test_token"
            assert headers["User-Agent"] == "agentops-python/1.2.3"

    def test_prepare_headers_with_custom_headers(self):
        """Test preparing headers with custom headers."""
        with patch("agentops.client.api.versions.v4.get_agentops_version", return_value="1.2.3"):
            custom_headers = {"X-Custom-Header": "custom_value"}
            headers = self.client.prepare_headers(custom_headers)

            assert headers["Authorization"] == "Bearer test_token"
            assert headers["User-Agent"] == "agentops-python/1.2.3"
            assert headers["X-Custom-Header"] == "custom_value"

    def test_prepare_headers_with_unknown_version(self):
        """Test preparing headers when version is unknown."""
        with patch("agentops.client.api.versions.v4.get_agentops_version", return_value=None):
            headers = self.client.prepare_headers()

            assert headers["Authorization"] == "Bearer test_token"
            assert headers["User-Agent"] == "agentops-python/unknown"

    def test_upload_object_success_string(self):
        """Test successful object upload with string body."""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"url": "http://example.com", "size": 123}

        with patch.object(self.client, "post", return_value=mock_response):
            result = self.client.upload_object("test content")

            # Check that result is a dict with the expected structure
            assert isinstance(result, dict)
            assert result["url"] == "http://example.com"
            assert result["size"] == 123
            self.client.post.assert_called_once_with(
                "/v4/objects/upload/", "test content", self.client.prepare_headers()
            )

    def test_upload_object_success_bytes(self):
        """Test successful object upload with bytes body."""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"url": "http://example.com", "size": 456}

        with patch.object(self.client, "post", return_value=mock_response):
            result = self.client.upload_object(b"test content")

            # Check that result is a dict with the expected structure
            assert isinstance(result, dict)
            assert result["url"] == "http://example.com"
            assert result["size"] == 456
            self.client.post.assert_called_once_with(
                "/v4/objects/upload/", "test content", self.client.prepare_headers()
            )

    def test_upload_object_http_error(self):
        """Test object upload with HTTP error."""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Bad request"}

        with patch.object(self.client, "post", return_value=mock_response):
            with pytest.raises(ApiServerException, match="Bad request"):
                self.client.upload_object("test content")

    def test_upload_object_http_error_no_error_field(self):
        """Test object upload with HTTP error but no error field in response."""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 500
        mock_response.json.return_value = {"message": "Internal error"}

        with patch.object(self.client, "post", return_value=mock_response):
            with pytest.raises(ApiServerException, match="Upload failed: 500"):
                self.client.upload_object("test content")

    def test_upload_object_http_error_json_parse_failure(self):
        """Test object upload with HTTP error and JSON parse failure."""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 404
        mock_response.json.side_effect = Exception("JSON error")

        with patch.object(self.client, "post", return_value=mock_response):
            with pytest.raises(ApiServerException, match="Upload failed: 404"):
                self.client.upload_object("test content")

    def test_upload_object_response_parse_failure(self):
        """Test object upload with successful HTTP but response parse failure."""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        # Make the json() call fail in the success block
        mock_response.json.side_effect = Exception("JSON parse error")

        with patch.object(self.client, "post", return_value=mock_response):
            with pytest.raises(ApiServerException, match="Failed to process upload response"):
                self.client.upload_object("test content")

    def test_upload_logfile_success_string(self):
        """Test successful logfile upload with string body."""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"url": "http://example.com/log", "size": 789}

        with patch.object(self.client, "post", return_value=mock_response):
            result = self.client.upload_logfile("log content", 123)

            # Check that result is a dict with the expected structure
            assert isinstance(result, dict)
            assert result["url"] == "http://example.com/log"
            assert result["size"] == 789

            # Check that the post was called with the correct headers including Trace-Id
            call_args = self.client.post.call_args
            assert call_args[0][0] == "/v4/logs/upload/"
            assert call_args[0][1] == "log content"
            headers = call_args[0][2]
            assert headers["Trace-Id"] == "123"
            assert headers["Authorization"] == "Bearer test_token"

    def test_upload_logfile_success_bytes(self):
        """Test successful logfile upload with bytes body."""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"url": "http://example.com/log", "size": 101}

        with patch.object(self.client, "post", return_value=mock_response):
            result = self.client.upload_logfile(b"log content", 456)

            # Check that result is a dict with the expected structure
            assert isinstance(result, dict)
            assert result["url"] == "http://example.com/log"
            assert result["size"] == 101

            # Check that the post was called with the correct headers including Trace-Id
            call_args = self.client.post.call_args
            assert call_args[0][0] == "/v4/logs/upload/"
            assert call_args[0][1] == "log content"
            headers = call_args[0][2]
            assert headers["Trace-Id"] == "456"
            assert headers["Authorization"] == "Bearer test_token"

    def test_upload_logfile_http_error(self):
        """Test logfile upload with HTTP error."""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 403
        mock_response.json.return_value = {"error": "Forbidden"}

        with patch.object(self.client, "post", return_value=mock_response):
            with pytest.raises(ApiServerException, match="Forbidden"):
                self.client.upload_logfile("log content", 123)

    def test_upload_logfile_http_error_no_error_field(self):
        """Test logfile upload with HTTP error but no error field in response."""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 500
        mock_response.json.return_value = {"message": "Internal error"}

        with patch.object(self.client, "post", return_value=mock_response):
            with pytest.raises(ApiServerException, match="Upload failed: 500"):
                self.client.upload_logfile("log content", 123)

    def test_upload_logfile_http_error_json_parse_failure(self):
        """Test logfile upload with HTTP error and JSON parse failure."""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 404
        mock_response.json.side_effect = Exception("JSON error")

        with patch.object(self.client, "post", return_value=mock_response):
            with pytest.raises(ApiServerException, match="Upload failed: 404"):
                self.client.upload_logfile("log content", 123)

    def test_upload_logfile_response_parse_failure(self):
        """Test logfile upload with successful HTTP but response parse failure."""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        # Make the json() call fail in the success block
        mock_response.json.side_effect = Exception("JSON parse error")

        with patch.object(self.client, "post", return_value=mock_response):
            with pytest.raises(ApiServerException, match="Failed to process upload response"):
                self.client.upload_logfile("log content", 123)
