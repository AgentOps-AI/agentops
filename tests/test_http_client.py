import unittest
from unittest.mock import patch, Mock
import requests

from agentops.http_client import (
    HttpClient,
    HttpStatus,
    dead_letter_queue,
    ApiServerException,
)


class TestHttpClient(unittest.TestCase):

    @patch("requests.Session")
    def test_post_success(self, mock_session):
        # Mock a successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": "Success"}

        mock_session_instance = mock_session.return_value
        mock_session_instance.post.return_value = mock_response

        url = "https://example.com/api"
        payload = b'{"key": "value"}'

        response = HttpClient.post(url, payload)

        self.assertEqual(response.code, 200)
        self.assertEqual(response.status, HttpStatus.SUCCESS)
        self.assertEqual(response.body, {"message": "Success"})

    @patch("requests.Session")
    def test_post_timeout(self, mock_session):
        # Mock a timeout exception
        mock_session_instance = mock_session.return_value
        mock_session_instance.post.side_effect = requests.exceptions.Timeout

        url = "https://example.com/api"
        payload = b'{"key": "value"}'

        with self.assertRaises(ApiServerException) as context:
            HttpClient.post(url, payload)

        self.assertIn("connection timed out", str(context.exception))
        self.assertEqual(len(dead_letter_queue.get_all()), 1)

    @patch("requests.Session")
    def test_post_http_error(self, mock_session):
        # Mock an HTTPError
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal Server Error"}
        mock_session_instance = mock_session.return_value
        mock_session_instance.post.side_effect = requests.exceptions.HTTPError(
            response=mock_response
        )

        url = "https://example.com/api"
        payload = b'{"key": "value"}'

        with self.assertRaises(ApiServerException) as context:
            HttpClient.post(url, payload)

        # self.assertIn("HTTPError", str(context.exception))
        self.assertEqual(len(dead_letter_queue.get_all()), 1)
        failed_request = dead_letter_queue.get_all()[0]
        self.assertEqual(failed_request["url"], url)
        self.assertEqual(failed_request["error_type"], "ServerError")

    @patch("requests.Session")
    def test_post_invalid_api_key(self, mock_session):
        # Mock a response with invalid API key
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Invalid API key"}

        mock_session_instance = mock_session.return_value
        mock_session_instance.post.return_value = mock_response

        url = "https://example.com/api"
        payload = b'{"key": "value"}'

        with self.assertRaises(ApiServerException) as context:
            HttpClient.post(url, payload, api_key="INVALID_KEY")

        self.assertIn("invalid API key", str(context.exception))
        self.assertEqual(len(dead_letter_queue.get_all()), 0)

    @patch("requests.Session")
    def test_get_success(self, mock_session):
        # Mock a successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": "Success"}

        mock_session_instance = mock_session.return_value
        mock_session_instance.get.return_value = mock_response

        url = "https://example.com/api"

        response = HttpClient.get(url)

        self.assertEqual(response.code, 200)
        self.assertEqual(response.status, HttpStatus.SUCCESS)
        self.assertEqual(response.body, {"message": "Success"})

    @patch("requests.Session")
    def test_get_timeout(self, mock_session):
        # Mock a timeout exception
        mock_session_instance = mock_session.return_value
        mock_session_instance.get.side_effect = requests.exceptions.Timeout

        url = "https://example.com/api"

        with self.assertRaises(ApiServerException) as context:
            HttpClient.get(url)

        self.assertIn("connection timed out", str(context.exception))
        self.assertEqual(len(dead_letter_queue.get_all()), 1)

    @patch("requests.Session")
    def test_get_http_error(self, mock_session):
        # Mock an HTTPError
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal Server Error"}

        mock_session_instance = mock_session.return_value
        mock_session_instance.get.side_effect = requests.exceptions.HTTPError(
            response=mock_response
        )

        url = "https://example.com/api"

        with self.assertRaises(ApiServerException) as context:
            HttpClient.get(url)

        self.assertEqual(len(dead_letter_queue.get_all()), 1)
        failed_request = dead_letter_queue.get_all()[0]
        self.assertEqual(failed_request["url"], url)
        self.assertEqual(failed_request["error_type"], "ServerError")

    def test_clear_dead_letter_queue(self):
        # Add a dummy request to DLQ and clear it
        dead_letter_queue.add(
            {"url": "https://example.com", "error_type": "DummyError"}
        )
        self.assertEqual(len(dead_letter_queue.get_all()), 1)

        dead_letter_queue.clear()
        self.assertEqual(len(dead_letter_queue.get_all()), 0)


if __name__ == "__main__":
    unittest.main()
