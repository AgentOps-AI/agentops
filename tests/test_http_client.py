import json
from uuid import uuid4

import pytest
import requests_mock

from agentops.http_client import HttpClient, HttpStatus
from agentops.exceptions import ApiServerException


@pytest.fixture(autouse=True)
def setup():
    """Reset HttpClient state before each test"""
    HttpClient._session = None
    HttpClient._jwt_store.clear()


def test_jwt_reauthorization_success(requests_mock):
    """Test successful JWT reauthorization flow"""
    session_id = str(uuid4())
    api_key = "test_key"
    endpoint = "https://api.example.com/v2"

    # Mock endpoints
    requests_mock.post(
        f"{endpoint}/some_endpoint",
        [
            {"status_code": 401, "json": {"error": "unauthorized"}},  # First call fails
            {"status_code": 200, "json": {"success": True}},  # Retry succeeds
        ],
    )
    requests_mock.post(f"{endpoint}/reauthorize_jwt", json={"jwt": "new_jwt_token"})

    # Make request that should trigger reauth
    response = HttpClient.post(
        f"{endpoint}/some_endpoint",
        json.dumps({"test": "data"}).encode("utf-8"),
        session_id=session_id,
        api_key=api_key,
    )

    # Verify
    assert response.status == HttpStatus.SUCCESS
    assert HttpClient.get_jwt(session_id) == "new_jwt_token"
    assert len(requests_mock.request_history) == 3  # Initial + reauth + retry


def test_jwt_reauthorization_failure(requests_mock):
    """Test failed JWT reauthorization"""
    session_id = str(uuid4())
    api_key = "test_key"
    endpoint = "https://api.example.com/v2"

    # Mock endpoints
    requests_mock.post(f"{endpoint}/some_endpoint", status_code=401, json={"error": "unauthorized"})
    requests_mock.post(f"{endpoint}/reauthorize_jwt", status_code=401, json={"error": "still unauthorized"})

    # Make request that should fail
    with pytest.raises(ApiServerException):
        HttpClient.post(
            f"{endpoint}/some_endpoint",
            json.dumps({"test": "data"}).encode("utf-8"),
            session_id=session_id,
            api_key=api_key,
        )

    # Verify JWT was cleared and correct number of requests made
    assert HttpClient.get_jwt(session_id) is None
    assert len(requests_mock.request_history) == 2


def test_jwt_storage_and_reuse(requests_mock):
    """Test JWT storage and reuse across requests"""
    session_id = str(uuid4())
    api_key = "test_key"
    test_jwt = "test_jwt_token"
    endpoint = "https://api.example.com/v2"

    # Mock endpoints
    requests_mock.post(f"{endpoint}/first_endpoint", json={"jwt": test_jwt, "success": True})
    requests_mock.post(f"{endpoint}/second_endpoint", json={"success": True})

    # Make first request that should store JWT
    HttpClient.post(
        f"{endpoint}/first_endpoint",
        json.dumps({"test": "data"}).encode("utf-8"),
        session_id=session_id,
        api_key=api_key,
    )

    # Make second request that should reuse JWT
    HttpClient.post(f"{endpoint}/second_endpoint", json.dumps({"test": "data"}).encode("utf-8"), session_id=session_id)

    # Verify JWT was reused
    assert requests_mock.request_history[1].headers["Authorization"] == f"Bearer {test_jwt}"


def test_jwt_cleared_on_401(requests_mock):
    """Test JWT is cleared when request returns 401"""
    session_id = str(uuid4())
    test_jwt = "test_jwt_token"
    endpoint = "https://api.example.com/v2"

    # Store a JWT
    HttpClient._jwt_store[session_id] = test_jwt

    # Mock endpoint
    requests_mock.post(f"{endpoint}/some_endpoint", status_code=401, json={"error": "unauthorized"})

    # Make request that should fail
    with pytest.raises(ApiServerException):
        HttpClient.post(
            f"{endpoint}/some_endpoint", json.dumps({"test": "data"}).encode("utf-8"), session_id=session_id
        )

    # Verify JWT was cleared
    assert HttpClient.get_jwt(session_id) is None


def test_error_responses(requests_mock):
    """Test various error responses"""
    endpoint = "https://api.example.com/v2"

    # Mock different error responses
    requests_mock.post(f"{endpoint}/bad_request", status_code=400, json={"message": "bad request"})
    requests_mock.post(f"{endpoint}/server_error", status_code=500, json={"message": "server error"})

    # Test 400 error
    with pytest.raises(ApiServerException, match="bad request"):
        HttpClient.post(f"{endpoint}/bad_request", json.dumps({}).encode("utf-8"))

    # Test 500 error
    with pytest.raises(ApiServerException, match="internal server error"):
        HttpClient.post(f"{endpoint}/server_error", json.dumps({}).encode("utf-8"))
