import uuid

import pytest
import requests_mock

from agentops.config import Config
from tests.fixtures.client import *  # noqa
from tests.unit.sdk.instrumentation_tester import InstrumentationTester


@pytest.fixture
def api_key() -> str:
    """Standard API key for testing"""
    return "test-api-key"


@pytest.fixture
def endpoint() -> str:
    """Base API URL"""
    return Config().endpoint


@pytest.fixture(autouse=True)
def mock_req(endpoint, api_key):
    """
    Mocks AgentOps backend API requests.
    """
    with requests_mock.Mocker(real_http=False) as m:
        # Map session IDs to their JWTs
        m.post(
            endpoint + "/v3/auth/token",
            json={"token": str(uuid.uuid4()), "project_id": "test-project-id", "api_key": api_key},
        )
        yield m


@pytest.fixture
def noinstrument():
    # Tells the client to not instrument LLM calls
    yield


@pytest.fixture
def mock_config(mocker):
    """Mock the Client.configure method"""
    return mocker.patch("agentops.client.Client.configure")


@pytest.fixture
def instrumentation():
    """Fixture for the instrumentation tester."""
    tester = InstrumentationTester()
    yield tester
    tester.reset()
