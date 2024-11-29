import json
from uuid import uuid4

import pytest
import requests_mock

import agentops
from agentops.config import Configuration


@pytest.fixture(autouse=True, scope="session")
def agentops_autoinit():
    agentops.init()
    yield


@pytest.fixture(scope="function")
def session(mock_req):
    """Create a test session"""
    # Start session through agentops
    session = agentops.start_session(tags=["test"])

    yield session

    # Cleanup
    try:
        if session:
            session.end_session("Success")
    except Exception as e:
        print(f"Error during session cleanup: {e}")

    # Clear all sessions
    agentops.end_all_sessions()

