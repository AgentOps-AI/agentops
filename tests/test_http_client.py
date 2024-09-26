import os
import unittest
from unittest.mock import patch, Mock, mock_open
import requests

from agentops.http_client import (
    HttpClient,
    HttpStatus,
    dead_letter_queue,
    ApiServerException,
)


@patch("builtins.open", new_callable=mock_open, read_data='{"messages": []}')
class TestHttpClient(unittest.TestCase):
    MAX_RETRIES = 3
    RETRY_DELAY = 1

    def setUp(self):
        # Clear DLQ before each test
        dead_letter_queue.is_testing = False
        dead_letter_queue.clear()
        self.addCleanup(patch.stopall)

    def tearDown(self):
        dead_letter_queue.is_testing = True
        dead_letter_queue.clear()

    @patch("requests.Session")
    def test_post_success(self, mock_session, mock_open_file):
        # Mock a successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": "Success"}

        mock_session_instance = mock_session.return_value
        mock_session_instance.post.return_value = mock_response

        url = "https://api.agentops.ai/health"
        payload = {"key": "value"}

        response = HttpClient.post(url, payload)

        self.assertEqual(response.code, 200)
        self.assertEqual(response.status, HttpStatus.SUCCESS)
        self.assertEqual(response.body, {"message": "Success"})

    @patch("requests.Session")
    def test_post_timeout(self, mock_session, mock_open_file):
        # Mock a timeout exception
        mock_session_instance = mock_session.return_value
        mock_session_instance.post.side_effect = requests.exceptions.Timeout

        url = "https://api.agentops.ai/health"
        payload = {"key": "value"}

        with self.assertRaises(ApiServerException) as context:
            HttpClient.post(url, payload)

        self.assertIn("timeout", str(context.exception).lower())
        self.assertEqual(len(dead_letter_queue.get_all()), 1)

    @patch("requests.Session")
    def test_post_http_error(self, mock_session, mock_open_file):
        # Mock an HTTPError
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal Server Error"}
        mock_session_instance = mock_session.return_value
        mock_session_instance.post.side_effect = requests.exceptions.HTTPError(
            response=mock_response
        )

        url = "https://api.agentops.ai/health"
        payload = {"key": "value"}

        with self.assertRaises(ApiServerException) as context:
            HttpClient.post(url, payload)

        # self.assertIn("HTTPError", str(context.exception))
        self.assertEqual(len(dead_letter_queue.get_all()), 1)
        failed_request = dead_letter_queue.get_all()[0]
        self.assertEqual(failed_request["url"], url)
        self.assertEqual(failed_request["error_type"], "HTTPError")

    @patch("requests.Session")
    def test_post_invalid_api_key(self, mock_session, mock_open_file):
        # Mock a response with invalid API key
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Invalid API key"}

        mock_session_instance = mock_session.return_value
        mock_session_instance.post.return_value = mock_response

        url = "https://api.agentops.ai/health"
        payload = {"key": "value"}

        with self.assertRaises(ApiServerException) as context:
            HttpClient.post(url, payload, api_key="INVALID_KEY")

        self.assertIn("invalid API key", str(context.exception))
        self.assertEqual(len(dead_letter_queue.get_all()), 0)

    @patch("requests.Session")
    def test_get_success(self, mock_session, mock_open_file):
        # Mock a successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": "Success"}

        mock_session_instance = mock_session.return_value
        mock_session_instance.get.return_value = mock_response

        url = "https://api.agentops.ai/health"

        response = HttpClient.get(url)

        self.assertEqual(response.code, 200)
        self.assertEqual(response.status, HttpStatus.SUCCESS)
        self.assertEqual(response.body, {"message": "Success"})

    @patch("requests.Session")
    def test_get_timeout(self, mock_session, mock_open_file):
        # Mock a timeout exception
        mock_session_instance = mock_session.return_value
        mock_session_instance.get.side_effect = requests.exceptions.Timeout

        url = "https://api.agentops.ai/health"

        with self.assertRaises(ApiServerException) as context:
            HttpClient.get(url)

        self.assertIn("timeout", str(context.exception).lower())
        self.assertEqual(len(dead_letter_queue.get_all()), 1)

    @patch("requests.Session")
    def test_get_http_error(self, mock_session, mock_open_file):
        # Mock an HTTPError
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal Server Error"}

        mock_session_instance = mock_session.return_value
        mock_session_instance.get.side_effect = requests.exceptions.HTTPError(
            response=mock_response
        )

        url = "https://api.agentops.ai/health"

        with self.assertRaises(ApiServerException) as context:
            HttpClient.get(url)

        self.assertEqual(len(dead_letter_queue.get_all()), 1)
        failed_request = dead_letter_queue.get_all()[0]
        self.assertEqual(failed_request["url"], url)
        self.assertEqual(failed_request["error_type"], "HTTPError")

    def test_clear_dead_letter_queue(self, mock_open_file):
        # Add a dummy request to DLQ and clear it
        dead_letter_queue.add(
            {"url": "https://api.agentops.ai/health", "error_type": "DummyError"}
        )
        self.assertEqual(len(dead_letter_queue.get_all()), 1)

        dead_letter_queue.clear()
        self.assertEqual(len(dead_letter_queue.get_all()), 0)

    @patch("requests.Session")
    def test_post_success_triggers_dlq_retry(self, mock_session, mock_open_file):
        # Mock successful POST response for the initial request
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"message": "Success"}

        mock_session_instance = mock_session.return_value
        mock_session_instance.post.side_effect = [
            mock_response_success,  # The initial post succeeds
            mock_response_success,  # The first DLQ retry succeeds
            mock_response_success,  # The second DLQ retry succeeds
        ]

        # Manually add failed requests to the DLQ
        failed_request_1 = {
            "url": "https://api.agentops.ai/health",
            "payload": {"key": "value1"},
            "api_key": "API_KEY_1",
            "parent_key": None,
            "jwt": None,
            "error_type": "Timeout",
        }
        failed_request_2 = {
            "url": "https://api.agentops.ai/health",
            "payload": {"key": "value2"},
            "api_key": "API_KEY_2",
            "parent_key": None,
            "jwt": None,
            "error_type": "Timeout",
        }
        dead_letter_queue.add(failed_request_1)
        dead_letter_queue.add(failed_request_2)

        # Perform an initial successful POST request
        url = "https://api.agentops.ai/health"
        payload = {"key": "value"}
        HttpClient.post(url, payload)

        # Check that both failed requests in the DLQ were retried and removed
        self.assertEqual(0, len(dead_letter_queue.get_all()))

    @patch("requests.Session")
    def test_dlq_retry_fails_and_stays_in_queue(self, mock_session, mock_open_file):
        # Mock successful POST response for the initial request
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"message": "Success"}

        # Mock failure for the DLQ retries
        mock_response_failure = Mock()
        mock_response_failure.status_code = 500
        mock_response_failure.json.return_value = {"error": "Internal Server Error"}

        mock_session_instance = mock_session.return_value
        mock_session_instance.post.side_effect = [
            mock_response_success,  # The initial post succeeds
            requests.exceptions.HTTPError(
                response=mock_response_failure
            ),  # First DLQ retry fails
        ]

        # Manually add a failed request to the DLQ
        failed_request = {
            "url": "https://api.agentops.ai/health",
            "payload": {"key": "value1"},
            "api_key": "API_KEY_1",
            "parent_key": None,
            "jwt": None,
            "error_type": "Timeout",
        }
        dead_letter_queue.add(failed_request)

        # Perform an initial successful POST request
        url = "https://api.agentops.ai/health"
        payload = b'{"key": "value"}'
        HttpClient.post(url, payload)

        # Check that the failed request is still in the DLQ since retry failed
        self.assertEqual(len(dead_letter_queue.get_all()), 1)

    @patch("requests.Session")
    def test_dlq_retry_successfully_retries_post_and_get(
        self, mock_session, mock_open_file
    ):
        # Mock successful POST and GET responses for DLQ retries
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"message": "Success"}

        mock_session_instance = mock_session.return_value
        mock_session_instance.post.side_effect = [
            mock_response_success,  # The initial post succeeds
            mock_response_success,  # The DLQ post retry succeeds
        ]
        mock_session_instance.get.side_effect = [
            mock_response_success,  # The DLQ get retry succeeds
        ]

        # Manually add failed POST and GET requests to the DLQ
        failed_post_request = {
            "url": "https://api.agentops.ai/health",
            "payload": {"key": "value1"},
            "api_key": "API_KEY_1",
            "parent_key": None,
            "jwt": None,
            "error_type": "Timeout",
        }
        failed_get_request = {
            "url": "https://api.agentops.ai/health",
            "payload": None,  # GET request
            "api_key": "API_KEY_2",
            "parent_key": None,
            "jwt": None,
            "error_type": "Timeout",
        }
        dead_letter_queue.add(failed_post_request)
        dead_letter_queue.add(failed_get_request)

        # Perform an initial successful POST request
        url = "https://api.agentops.ai/health"
        payload = {"key": "value"}
        HttpClient.post(url, payload)

        # Check that both failed requests (POST and GET) in the DLQ were retried and removed
        self.assertEqual(len(dead_letter_queue.get_all()), 0)

    def test_clear_dlq_after_success(self, mock_open_file):
        # Add requests to DLQ and ensure they are removed after retry success
        failed_request = {
            "url": "https://api.agentops.ai/health",
            "payload": {"key": "value1"},
            "api_key": "API_KEY_1",
            "parent_key": None,
            "jwt": None,
            "error_type": "Timeout",
        }
        dead_letter_queue.add(failed_request)

        # Ensure the DLQ has one request
        self.assertEqual(len(dead_letter_queue.get_all()), 1)

        # Clear the DLQ
        dead_letter_queue.clear()

        # Ensure the DLQ is empty
        self.assertEqual(len(dead_letter_queue.get_all()), 0)


if __name__ == "__main__":
    unittest.main()
