import unittest
from unittest.mock import patch, MagicMock, call
import time
# Note: Requires PyJWT package (pip install PyJWT)
import jwt
from datetime import datetime, timedelta

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExportResult

from agentops.client.exporters import AuthenticatedOTLPExporter
from agentops.client.api import ApiClient
from agentops.exceptions import ApiServerException


class TestOTLPExporterAuthentication(unittest.TestCase):
    """Test the OTLP exporter authentication mechanism"""

    def setUp(self):
        """Set up test fixtures"""
        self.api_key = "test-api-key"
        self.endpoint = "https://example.com/v1/traces"
        
        # Create a mock API client
        self.api_client = MagicMock(spec=ApiClient)
        
        # Mock spans for testing
        self.mock_spans = [MagicMock(spec=ReadableSpan) for _ in range(3)]
        
        # Create the exporter with our mock client
        self.exporter = AuthenticatedOTLPExporter(
            endpoint=self.endpoint,
            api_client=self.api_client,
            api_key=self.api_key
        )
        
        # Patch the parent class's export method to avoid actual network calls
        self.export_patcher = patch('opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter.export')
        self.mock_super_export = self.export_patcher.start()
        self.mock_super_export.return_value = SpanExportResult.SUCCESS
    
    def tearDown(self):
        """Clean up after tests"""
        self.export_patcher.stop()
    
    def generate_mock_token(self, expired=False):
        """Generate a mock JWT token that is either valid or expired"""
        expiry = datetime.now() - timedelta(hours=1) if expired else datetime.now() + timedelta(hours=1)
        
        payload = {
            'exp': expiry.timestamp(),
            'iat': datetime.now().timestamp(),
            'sub': 'test-subject'
        }
        
        # Using a dummy secret for test - real tokens would come from the API
        token = jwt.encode(payload, 'test-secret', algorithm='HS256')
        return token
    
    def test_gets_fresh_token_on_export(self):
        """Test that exporter gets a fresh token before export"""
        # Setup initial auth headers
        initial_token = self.generate_mock_token()
        self.api_client.get_auth_headers.return_value = {
            'Authorization': f'Bearer {initial_token}',
            'X-Agentops-Api-Key': self.api_key
        }
        
        # Export spans
        result = self.exporter.export(self.mock_spans)
        
        # Verify API client was called to get auth headers
        self.api_client.get_auth_headers.assert_called_once_with(self.api_key, {})
        
        # Verify headers were updated before export
        self.mock_super_export.assert_called_once_with(self.mock_spans)
        
        # Verify the result is passed through
        self.assertEqual(result, SpanExportResult.SUCCESS)
    
    def test_token_refreshed_when_expired(self):
        """Test that token is refreshed when expired"""
        # Mock the API client's get_auth_headers method to simulate token expiration
        # First call returns headers with an expired token, second call returns fresh token
        expired_token = self.generate_mock_token(expired=True)
        fresh_token = self.generate_mock_token(expired=False)
        
        # Configure the API client to simulate token refresh
        self.api_client.get_valid_token.side_effect = [
            expired_token,  # First call - returns expired token
            fresh_token     # Second call after refresh - returns fresh token
        ]
        
        # Configure get_auth_headers to use the token from get_valid_token
        def mock_get_auth_headers(api_key, custom_headers=None):
            token = self.api_client.get_valid_token(api_key)
            return {
                'Authorization': f'Bearer {token}',
                'X-Agentops-Api-Key': api_key
            }
        
        self.api_client.get_auth_headers.side_effect = mock_get_auth_headers
        
        # First export should use the expired token (in a real scenario, the ApiClient
        # would detect this and refresh it)
        self.exporter.export(self.mock_spans)
        
        # Modify is_token_valid to simulate expiry detection
        self.api_client.is_token_valid.return_value = False
        
        # Second export should detect expired token and get a fresh one
        self.exporter.export(self.mock_spans)
        
        # Verify get_valid_token was called twice
        self.assertEqual(self.api_client.get_valid_token.call_count, 2)
        
        # Verify token refresh logic in get_valid_token was triggered
        self.api_client.is_token_valid.assert_called()
    
    def test_handles_auth_error(self):
        """Test that exporter handles authentication errors gracefully"""
        # Make the API client raise an exception during authentication
        self.api_client.get_auth_headers.side_effect = ApiServerException("Auth failed")
        
        # Export should propagate the exception since it's critical
        with self.assertRaises(ApiServerException):
            self.exporter.export(self.mock_spans)
        
        # Verify API client was called
        self.api_client.get_auth_headers.assert_called_once()
        
        # Verify super().export was not called due to auth failure
        self.mock_super_export.assert_not_called()
    
    def test_integration_with_api_client_refresh(self):
        """Test the integration between exporter and API client token refresh"""
        # Create a more realistic API client mock that simulates token refresh logic
        api_client = MagicMock(spec=ApiClient)
        
        # First call to is_token_valid returns True (token valid)
        # Second call returns False (token expired)
        api_client.is_token_valid.side_effect = [True, False, True]
        
        # Valid token for first call
        valid_token = self.generate_mock_token()
        # New token after refresh
        new_token = self.generate_mock_token()
        
        # First get_valid_token returns existing token
        # Second call triggers refresh and returns new token
        api_client.get_valid_token.side_effect = [valid_token, new_token]
        
        # Configure auth headers based on the current token
        def get_auth_headers(api_key, custom_headers=None):
            token = api_client.get_valid_token(api_key)
            return {
                'Authorization': f'Bearer {token}',
                'X-Agentops-Api-Key': api_key
            }
        
        api_client.get_auth_headers.side_effect = get_auth_headers
        
        # Create exporter with our realistic mock
        exporter = AuthenticatedOTLPExporter(
            endpoint=self.endpoint,
            api_client=api_client,
            api_key=self.api_key
        )
        
        # First export - token is valid
        exporter.export(self.mock_spans)
        
        # Verify first export used valid token without refresh
        self.assertEqual(api_client.get_valid_token.call_count, 1)
        self.assertEqual(api_client.is_token_valid.call_count, 1)
        
        # Second export - token is now expired and should be refreshed
        exporter.export(self.mock_spans)
        
        # Verify token was checked again and refreshed
        self.assertEqual(api_client.get_valid_token.call_count, 2)
        self.assertEqual(api_client.is_token_valid.call_count, 2)
        
        # Verify the super class's export was called twice
        self.assertEqual(self.mock_super_export.call_count, 2)


if __name__ == '__main__':
    unittest.main() 