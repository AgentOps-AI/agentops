import pytest
from pytest_mock import MockerFixture

from agentops import Client


@pytest.fixture(autouse=True)
def reset_client():
    """Reset the client singleton before and after each test"""
    # Reset the Client singleton by resetting its class attributes
    Client.__instance = None
    if hasattr(Client, "_init_done"):
        delattr(Client, "_init_done")
    yield
    # Reset again after the test
    Client.__instance = None
    if hasattr(Client, "_init_done"):
        delattr(Client, "_init_done")
