import pytest
import requests
from unittest.mock import patch
from agentops.client.http.http_client import HttpClient
from agentops.helpers.version import get_agentops_version


@pytest.fixture(autouse=True)
def reset_http_client_session():
    # Reset the cached session before each test
    HttpClient._session = None


def test_user_agent_header():
    with patch("requests.Session", wraps=requests.Session):
        session = HttpClient.get_session()
        expected_version = get_agentops_version() or "unknown"
        expected_user_agent = f"agentops-python/{expected_version}"
        # Check the session's headers directly
        assert "User-Agent" in session.headers
        assert session.headers["User-Agent"] == expected_user_agent


def test_user_agent_header_content():
    with patch("requests.Session", wraps=requests.Session):
        session = HttpClient.get_session()
        # Check the session's headers directly
        assert "User-Agent" in session.headers
        assert "Connection" in session.headers
        assert "Keep-Alive" in session.headers
        assert "Content-Type" in session.headers
        assert session.headers["Connection"] == "keep-alive"
        assert session.headers["Keep-Alive"] == "timeout=10, max=1000"
        assert session.headers["Content-Type"] == "application/json"
