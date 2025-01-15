import pytest
import concurrent.futures
from fastapi import FastAPI
from fastapi.testclient import TestClient
import agentops
from agentops import record_tool
import time

# Create FastAPI app
app = FastAPI()


@app.get("/completion")
def completion():
    start_time = time.time()

    @record_tool(tool_name="foo")
    def foo(x: str):
        print(x)

    foo("Hello")

    end_time = time.time()
    execution_time = end_time - start_time

    return {"response": "Done", "execution_time_seconds": round(execution_time, 3)}


pytestmark = [pytest.mark.integration]


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def setup_agentops():
    agentops.init(auto_start_session=True)  # Let agentops handle sessions automatically
    yield
    agentops.end_all_sessions()


def test_concurrent_api_requests(client):
    """Test concurrent API requests to ensure proper session handling."""

    def fetch_url(test_client):
        response = test_client.get("/completion")
        assert response.status_code == 200
        return response.json()

    # Make concurrent requests
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(fetch_url, client), executor.submit(fetch_url, client)]
        responses = [future.result() for future in concurrent.futures.as_completed(futures)]

    # Verify responses
    assert len(responses) == 2
    for response in responses:
        assert "response" in response
        assert response["response"] == "Done"
        assert "execution_time_seconds" in response
        assert isinstance(response["execution_time_seconds"], float)
