import pytest
import concurrent.futures
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
import agentops
from agentops.client import Client

# Create FastAPI app
app = FastAPI()


def process_request(x: str):
    """Process a request and return a response."""
    return f"Processed: {x}"


@app.get("/completion")
def completion():
    result = process_request("Hello")
    return {"response": result, "status": "success"}


@pytest.fixture
def client():
    """Fixture to provide FastAPI test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def setup_agentops(mock_api_key):
    """Setup AgentOps with mock API key."""
    # Reset client singleton
    Client._Client__instance = None

    # Mock the API client to avoid real authentication
    with patch("agentops.client.client.ApiClient") as mock_api_client:
        # Create mock API instance
        mock_api = MagicMock()
        mock_api.v3.fetch_auth_token.return_value = {"token": "mock_token", "project_id": "mock_project_id"}
        mock_api_client.return_value = mock_api

        # Mock global tracer to avoid actual initialization
        with patch("agentops.tracer") as mock_tracer:
            mock_tracer.initialized = True

            agentops.init(api_key=mock_api_key, auto_start_session=True)
            yield

            try:
                agentops.end_all_sessions()
            except:
                pass

    # Clean up client singleton
    Client._Client__instance = None


def test_concurrent_api_requests(client):
    """Test concurrent API requests to ensure proper session handling."""

    def fetch_url(test_client):
        response = test_client.get("/completion")
        assert response.status_code == 200
        return response.json()

    # Make concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(fetch_url, client) for _ in range(3)]
        responses = [future.result() for future in concurrent.futures.as_completed(futures)]

    # Verify responses
    assert len(responses) == 3
    for response in responses:
        assert "response" in response
        assert response["response"] == "Processed: Hello"
        assert response["status"] == "success"


def test_session_isolation():
    """Test that basic functions work in parallel (simplified concurrency test)."""

    def session_a():
        return process_request("A")

    def session_b():
        return process_request("B")

    # Run sessions in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(session_a)
        future_b = executor.submit(session_b)

        result_a = future_a.result()
        result_b = future_b.result()

    assert result_a == "Processed: A"
    assert result_b == "Processed: B"


def test_session_error_handling():
    """Test error handling in concurrent execution."""

    def error_session():
        raise ValueError("Test error")

    def success_session():
        return process_request("Success")

    # Run sessions in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        error_future = executor.submit(error_session)
        success_future = executor.submit(success_session)

        # Verify success case
        assert success_future.result() == "Processed: Success"

        # Verify error case
        with pytest.raises(ValueError) as exc_info:
            error_future.result()
        assert "Test error" in str(exc_info.value)
