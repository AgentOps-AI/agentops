import pytest

from agentops import Client


@pytest.fixture(autouse=True)
def reset_client():
    """Reset the client singleton before and after each test"""
    # Reset the Client singleton by resetting its class attributes
    if getattr(Client, "__instance", None):
        del Client.__instance
    yield
    # Reset again after the test
    Client.__instance = None


@pytest.fixture(autouse=True)
def mock_client(reset_client):
    # Resets the client with a clear env
    Client()
    yield
