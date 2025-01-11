import contextlib
from typing import Iterator

import pytest
import requests_mock
from pytest import Config, Session

import agentops
from agentops.singleton import clear_singletons
from tests.fixtures.event import llm_event_spy
from tests.fixtures.vcr import vcr_config

# Common JWT tokens used across tests
JWTS = ["some_jwt", "some_jwt2", "some_jwt3"]


@pytest.fixture(autouse=True)
def setup_teardown():
    """
    Ensures that all agentops sessions are closed and singletons are cleared in-between tests
    """
    clear_singletons()
    yield
    agentops.end_all_sessions()  # teardown part


@pytest.fixture(scope="session")
def api_key() -> str:
    """Standard API key for testing"""
    return "11111111-1111-4111-8111-111111111111"


@pytest.fixture(scope="session")
def base_url() -> str:
    """Base API URL"""
    return "https://api.agentops.ai"
