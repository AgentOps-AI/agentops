import pytest
from fastapi.testclient import TestClient
import jockey.api.main as main


@pytest.fixture(autouse=True)
def disable_background(monkeypatch):
    """Disable background deployment thread and event generation."""
    monkeypatch.setattr("jockey.worker.queue.health_check", lambda: True)
    monkeypatch.setattr("jockey.worker.queue.get_queue_length", lambda: 0)
    monkeypatch.setattr("jockey.worker.queue.get_processing_count", lambda: 0)


@pytest.fixture
def client():
    """Test client for the FastAPI app."""
    return TestClient(main.app)


def test_health_check_healthy(client, monkeypatch):
    # The health check uses the mocked queue.health_check() from the fixture
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "redis": "connected"}


def test_health_check_unhealthy(client, monkeypatch):
    # Override the health check to simulate failure
    monkeypatch.setattr("jockey.worker.queue.health_check", lambda: False)
    response = client.get("/health")
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "unhealthy"
    assert result["redis"] == "disconnected"
