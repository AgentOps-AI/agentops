"""Tests for OpenAI Assistants API integration."""

import pytest
from unittest.mock import Mock, patch
from uuid import UUID
from agentops.integrations.openai_assistants import AssistantAgent
from agentops.session import Session
from agentops.event import LLMEvent, ToolEvent
from agentops.config import Configuration


@pytest.fixture
def mock_openai():
    with patch("agentops.integrations.openai_assistants.OpenAI") as mock:
        # Mock client for configuration
        mock_client = Mock()
        mock_client.add_pre_init_warning = Mock()

        # Mock assistant with proper name attribute
        assistant_mock = Mock()
        assistant_mock.id = "test_assistant"
        assistant_mock.model = "gpt-4"
        assistant_mock.name = "Test Assistant"
        mock.return_value.beta.assistants.retrieve.return_value = assistant_mock

        # Mock thread
        mock.return_value.beta.threads.create.return_value = Mock(id="test_thread")

        # Mock message
        mock.return_value.beta.threads.messages.create.return_value = Mock(id="test_message")

        # Mock run with valid UUID thread_id
        run_mock = Mock()
        run_mock.id = "test_run"
        run_mock.thread_id = "12345678-1234-5678-1234-567812345678"
        run_mock.status = "completed"
        run_mock.model = "gpt-4"
        mock.return_value.beta.threads.runs.create.return_value = run_mock
        mock.return_value.beta.threads.runs.retrieve.return_value = run_mock

        # Mock HttpClient for session creation
        with patch("agentops.session.HttpClient") as http_mock:
            response_mock = Mock()
            response_mock.code = 200
            response_mock.body = {"jwt": "test-jwt"}
            http_mock.post.return_value = response_mock
            yield mock, mock_client


def test_assistant_creation(mock_openai):
    mock_openai_client, mock_client = mock_openai
    config = Configuration()
    config.configure(mock_client, api_key="12345678-1234-5678-1234-567812345678")
    session = Session(session_id=UUID("12345678-1234-5678-1234-567812345678"), config=config)
    agent = AssistantAgent("test_assistant", session)

    assert agent.assistant_id == "test_assistant"
    assert agent.model == "gpt-4"
    assert agent.name == "Test Assistant"


def test_thread_creation(mock_openai):
    mock_openai_client, mock_client = mock_openai
    config = Configuration()
    config.configure(mock_client, api_key="12345678-1234-5678-1234-567812345678")
    session = Session(session_id=UUID("12345678-1234-5678-1234-567812345678"), config=config)
    agent = AssistantAgent("test_assistant", session)

    thread_id = agent.create_thread()
    assert thread_id == "test_thread"
    assert session.thread_id == "test_thread"


def test_run_recording(mock_openai):
    mock_openai_client, mock_client = mock_openai
    config = Configuration()
    config.configure(mock_client, api_key="12345678-1234-5678-1234-567812345678")
    session = Session(session_id=UUID("12345678-1234-5678-1234-567812345678"), config=config)

    # Debug: verify session is running
    assert session.is_running, "Session failed to start"

    agent = AssistantAgent("test_assistant", session)
    thread_id = agent.create_thread()
    result = agent.run(thread_id)

    # Debug: print event counts
    print("Event counts:", session.event_counts)

    # Verify LLMEvent was recorded
    assert session.event_counts["llms"] > 0
