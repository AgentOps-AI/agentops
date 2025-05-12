import pytest
import concurrent.futures
from unittest.mock import MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
import agentops
from agentops.sdk.decorators import operation, session

# Create FastAPI app
app = FastAPI()


@operation
def process_request(x: str):
    """Process a request and return a response."""
    return f"Processed: {x}"


@session
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
    agentops.init(api_key=mock_api_key, auto_start_session=True)
    yield
    agentops.end_all_sessions()


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
    """Test that sessions are properly isolated."""

    @session
    def session_a():
        return process_request("A")

    @session
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
    """Test error handling in concurrent sessions."""

    @session
    def error_session():
        raise ValueError("Test error")

    @session
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
