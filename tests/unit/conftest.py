import contextlib
from typing import Iterator

import pytest
import requests_mock
from pytest import Config, Session

import agentops
from agentops.singleton import clear_singletons
from tests.fixtures.event import llm_event_spy

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


# @contextlib.contextmanager
# @pytest.fixture(autouse=True)
# def mock_req() -> Iterator[requests_mock.Mocker]:
#     """
#     Centralized request mocking for all tests.
#     Mocks common API endpoints with standard responses.
#     """
#     with requests_mock.Mocker() as m:
#         url = "https://api.agentops.ai"
#
#         # Mock API endpoints
#         m.post(url + "/v2/create_events", json={"status": "ok"})
#         m.post(url + "/v2/developer_errors", json={"status": "ok"})
#         m.post(url + "/v2/update_session", json={"status": "success", "token_cost": 5})
#         m.post("https://pypi.org/pypi/agentops/json", status_code=404)
#
#         # Use iterator for JWT tokens in session creation
#         jwt_tokens = iter(JWTS)
#
#         def create_session_response(request, context):
#             context.status_code = 200
#             try:
#                 return {"status": "success", "jwt": next(jwt_tokens)}
#             except StopIteration:
#                 return {"status": "success", "jwt": "some_jwt"}  # Fallback JWT
#
#         m.post(url + "/v2/create_session", json=create_session_response)
#         m.post(url + "/v2/reauthorize_jwt", json={"status": "success", "jwt": "some_jwt"})
#
#         yield m


@pytest.fixture(scope="session")
def api_key() -> str:
    """Standard API key for testing"""
    return "11111111-1111-4111-8111-111111111111"


@pytest.fixture(scope="session")
def base_url() -> str:
    """Base API URL"""
    return "https://api.agentops.ai"
