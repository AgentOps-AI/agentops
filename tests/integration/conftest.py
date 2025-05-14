import pytest
from unittest.mock import MagicMock

import agentops

import openai
import anthropic
from agentops.client import Client


@pytest.fixture
def mock_api_key():
    """Fixture to provide a mock API key."""
    return "test-api-key-" + "x" * 32


@pytest.fixture
def mock_auth_response():
    """Fixture to provide a mock authentication response."""
    return MagicMock(status_code=200, json=lambda: {"access_token": "mock_token"})


@pytest.fixture
def agentops_client(mock_api_key, monkeypatch):
    """Fixture to provide an initialized AgentOps client."""
    # Create a mock auth response
    mock_auth = MagicMock()
    mock_auth.authenticate = lambda x: True
    mock_auth.is_authenticated = True

    # Create the client
    client = Client()

    # Mock the auth module
    monkeypatch.setattr(client, "api", MagicMock(auth=mock_auth))

    # Initialize with mock key
    client.init(api_key=mock_api_key)
    return client


@pytest.fixture
def agentops_session(agentops_client):
    """Fixture to manage AgentOps session."""
    agentops.start_session()
    yield
    agentops.end_all_sessions()


@pytest.fixture
def openai_client():
    """Fixture to provide OpenAI client with mock API key."""
    client = openai.OpenAI(api_key="test-openai-key")
    # Mock the completions API
    client.chat.completions.create = MagicMock()
    return client


@pytest.fixture
def anthropic_client():
    """Fixture to provide Anthropic client with mock API key."""
    client = anthropic.Anthropic(api_key="test-anthropic-key")
    # Mock the messages API
    client.messages.create = MagicMock()
    return client


@pytest.fixture
def test_messages():
    """Fixture to provide test messages."""
    return [{"role": "user", "content": "Write a short greeting."}]


@pytest.fixture
def mock_response():
    """Fixture to provide a mock response for testing."""
    return MagicMock(choices=[MagicMock(message=MagicMock(content="Hello! This is a test response."))])


@pytest.fixture
def mock_stream_response():
    """Fixture to provide a mock streaming response."""
    return [
        MagicMock(choices=[MagicMock(delta=MagicMock(content="Hello"))]),
        MagicMock(choices=[MagicMock(delta=MagicMock(content=" World!"))]),
    ]
