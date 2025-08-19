import agentops
import pytest
from agentops import Session
from datetime import datetime
import requests


@pytest.fixture
def agentops_init():
    agentops.init()


@pytest.fixture
def agentops_session(agentops_init):
    """Create an agentops session"""
    session = agentops.start_session()

    assert session, "Failed agentops.start_session() returned None."
    yield session
    agentops.end_all_sessions()


def test_logs_read_write_to_session(agentops_session: Session):
    """
    Subsequently tests `/v3/logs/{session_id}` endpoint for PUT -> GET.
    """
    session_id = str(agentops_session.session_id)
    api_base = "http://localhost:8000"  # Or get from environment variable

    # Test writing to session
    test_data = {
        "stdout_line_count": 5,
        "stderr_line_count": 1,
        "log_level_counts": {"INFO": 3, "WARNING": 2},
        "start_time": datetime.now().isoformat(),
        "end_time": datetime.now().isoformat(),
        "is_capturing": False,
        "logs": [
            {"level": "INFO", "message": "Test write log 1"},
            {"level": "WARNING", "message": "Test warning 1"},
            {"level": "INFO", "message": "Test write log 2"},
        ],
    }

    # Write logs using real HTTP request
    response = requests.put(
        f"{api_base}/v3/logs/{session_id}",
        json=test_data,
        headers={"Authorization": f"Bearer {agentops_session.jwt}"},
    )

    assert response.status_code == 200
    write_response = response.json()
    assert write_response["status"] == "success"
    assert write_response["session_id"] == session_id
    assert "url" in write_response
    assert "filename" in write_response

    # Read logs back using real HTTP request
    response = requests.get(
        f"{api_base}/v3/logs/{session_id}",
        headers={"Authorization": f"Bearer {agentops_session.jwt}"},
    )

    assert response.status_code == 200
    read_response = response.json()
    assert read_response["session_id"] == session_id
    assert "logs" in read_response
    assert len(read_response["logs"]) > 0

    # Verify the log file we just wrote is in the response
    found_file = False
    for log_file in read_response["logs"]:
        if log_file["name"] == write_response["filename"]:
            found_file = True
            assert "url" in log_file
            assert "created_at" in log_file
            break

    assert found_file, "Could not find the written log file in the GET response"
