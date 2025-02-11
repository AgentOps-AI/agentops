import contextlib
import re
import uuid
from collections import defaultdict
from typing import Dict, Iterator, List

import pytest
import requests_mock
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from pytest import Config, Session

import agentops
from agentops.event import ActionEvent, ErrorEvent, LLMEvent, ToolEvent
from agentops.instrumentation import SessionTracer
from agentops.singleton import clear_singletons
from tests.fixtures.event import llm_event_spy


@pytest.fixture
def jwt():
    """Fixture that provides unique JWTs per session within a test"""
    session_jwts = defaultdict(lambda: str(uuid.uuid4()))
    session_count = 0

    def get_jwt():
        nonlocal session_count
        jwt = session_jwts[session_count]
        session_count += 1
        return jwt

    return get_jwt


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
    return agentops.Client()._config.endpoint


@pytest.fixture(autouse=True)
def mock_req(base_url, jwt):
    """
    Mocks AgentOps backend API requests.
    """
    with requests_mock.Mocker() as m:
        # Map session IDs to their JWTs
        m.session_jwts = {}

        m.post(base_url + "/v2/create_events", json={"status": "ok"})

        def create_session_response(request, context):
            context.status_code = 200
            # Extract session_id from the request
            session_id = request.json()["session"]["session_id"]
            # Use the jwt fixture to get consistent JWTs
            m.session_jwts[session_id] = jwt()
            return {"status": "success", "jwt": m.session_jwts[session_id]}

        def reauthorize_jwt_response(request, context):
            context.status_code = 200
            # Extract session_id from the request
            session_id = request.json()["session_id"]
            # Return the same JWT for this session
            return {"status": "success", "jwt": m.session_jwts[session_id]}

        m.post(base_url + "/v2/create_session", json=create_session_response)
        m.post(base_url + "/v2/update_session", json={"status": "success", "token_cost": 5})
        m.post(base_url + "/v2/developer_errors", json={"status": "ok"})
        m.post(base_url + "/v2/reauthorize_jwt", json=reauthorize_jwt_response)
        m.post(base_url + "/v2/create_agent", json={"status": "success"})
        m.post(base_url + "/v2/create_events", json={"status": "success"})
        # Use explicit regex pattern for logs endpoint to match any URL and session ID
        logs_pattern = re.compile(r".*/v3/logs/[0-9a-f-]{8}-[0-9a-f-]{4}-[0-9a-f-]{4}-[0-9a-f-]{4}-[0-9a-f-]{12}")
        m.put(logs_pattern, json={"status": "success"})
        m.get(logs_pattern, json={"status": "success"})

        yield m


@pytest.fixture
def agentops_init(api_key, base_url):
    agentops.init(api_key=api_key, endpoint=base_url)


@pytest.fixture
def agentops_session(agentops_init):
    session = agentops.start_session()

    assert session, "Failed agentops.start_session() returned None."

    yield session

    agentops.end_all_sessions()


@pytest.fixture
def mock_llm_event():
    """Creates an LLMEvent for testing"""
    return LLMEvent(
        prompt="What is the meaning of life?",
        completion="42",
        model="gpt-4",
        prompt_tokens=10,
        completion_tokens=1,
        cost=0.01,
    )


@pytest.fixture
def mock_action_event():
    """Creates an ActionEvent for testing"""
    return ActionEvent(
        action_type="process_data",
        params={"input_file": "data.csv"},
        returns="100 rows processed",
        logs="Successfully processed all rows",
    )


@pytest.fixture
def mock_tool_event():
    """Creates a ToolEvent for testing"""
    return ToolEvent(
        name="searchWeb",
        params={"query": "python testing"},
        returns=["result1", "result2"],
        logs={"status": "success"},
    )


@pytest.fixture
def mock_error_event():
    """Creates an ErrorEvent for testing"""
    trigger = ActionEvent(action_type="risky_action")
    error = ValueError("Something went wrong")
    return ErrorEvent(trigger_event=trigger, exception=error, error_type="ValueError", details="Detailed error info")


@pytest.fixture(autouse=True)
def sync_tracer(mocker):
    """Fixture to make SessionTracer use SimpleSpanProcessor for synchronous export during tests"""

    mocker.patch("agentops.instrumentation.SessionTracer.exporter_cls", return_value=SimpleSpanProcessor)
    yield
