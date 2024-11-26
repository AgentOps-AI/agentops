import pytest
import requests_mock
from unittest.mock import Mock
from uuid import uuid4
from agentops.config import Configuration


@pytest.fixture(autouse=True)
def mock_req():
    """Mock HTTP requests for all tests"""
    with requests_mock.Mocker() as m:
        url = "https://api.agentops.ai"
        m.post(url + "/v2/create_session", json={"status": "success", "jwt": "test_jwt"})
        m.post(url + "/v2/create_events", json={"status": "ok"})
        m.post(url + "/v2/update_session", json={"status": "success"})
        m.post(url + "/v2/reauthorize_jwt", json={"status": "success", "jwt": "test_jwt"})
        yield m
