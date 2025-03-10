import os
import re
import uuid
from collections import defaultdict
from unittest import mock

import pytest
import requests_mock

import agentops
from agentops.config import Config
from tests.fixtures.client import *  # noqa


@pytest.fixture
def api_key() -> str:
    """Standard API key for testing"""
    return "test-api-key"


@pytest.fixture
def endpoint() -> str:
    """Base API URL"""
    return Config().endpoint


@pytest.fixture(autouse=True)
def mock_req(endpoint):
    """
    Mocks AgentOps backend API requests.
    """
    with requests_mock.Mocker(real_http=False) as m:
        # Map session IDs to their JWTs
        m.post(endpoint + "/v3/auth/token", json={"token": str(uuid.uuid4())})
        yield m
