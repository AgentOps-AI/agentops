import re
import uuid
from collections import defaultdict

import pytest
import requests_mock

import agentops
from agentops.config import Config
from tests.fixtures.client import *  # noqa
from tests.fixtures.config import *  # noqa
from tests.fixtures.instrumentation import *  # noqa
from tests.fixtures.session import *  # noqa


@pytest.fixture(autouse=True)
def setup_teardown():
    """
    Ensures that all agentops sessions are closed and singletons are cleared in-between tests
    """
    yield
    agentops.end_all_sessions()  # teardown part


@pytest.fixture
def api_key(agentops_config) -> str:
    """Standard API key for testing"""
    return agentops_config.api_key


@pytest.fixture
def base_url(agentops_config) -> str:
    """Base API URL"""
    return agentops_config.endpoint


@pytest.fixture(autouse=True)
def mock_req(agentops_config):
    """
    Mocks AgentOps backend API requests.
    """
    with requests_mock.Mocker(real_http=False) as m:
        # Map session IDs to their JWTs
        m.post(agentops_config.endpoint + "/v3/auth/token", json={"token": str(uuid.uuid4())})
        yield m


@pytest.fixture
def agentops_init(api_key, agentops_config):
    agentops.init(api_key=api_key, endpoint=agentops_config.endpoint, auto_start_session=False)


@pytest.fixture(autouse=True)
def noinstrument(agentops_config):
    agentops_config.instrument_llm_calls = False
    yield

@pytest.fixture
def instrument(agentops_config, noinstrument):
    agentops_config.instrument_llm_calls = True
    yield
