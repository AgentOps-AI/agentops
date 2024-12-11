"""Tests for OpenAI Assistants API integration."""

import pytest
from unittest.mock import Mock, patch
from uuid import UUID
from agentops.integrations.openai_assistants import AssistantAgent
from agentops.session import Session
from agentops.event import LLMEvent, ToolEvent

@pytest.fixture
def mock_openai():
    with patch('agentops.integrations.openai_assistants.OpenAI') as mock:
        # Mock assistant
        mock.return_value.beta.assistants.retrieve.return_value = Mock(
            id='test_assistant',
            model='gpt-4',
            name='Test Assistant'
        )

        # Mock thread
        mock.return_value.beta.threads.create.return_value = Mock(
            id='test_thread'
        )

        # Mock message
        mock.return_value.beta.threads.messages.create.return_value = Mock(
            id='test_message'
        )

        # Mock run
        mock.return_value.beta.threads.runs.create.return_value = Mock(
            id='test_run',
            thread_id='test_thread',
            status='completed',
            model='gpt-4'
        )

        yield mock

def test_assistant_creation(mock_openai):
    session = Session()
    agent = AssistantAgent('test_assistant', session)

    assert agent.assistant_id == 'test_assistant'
    assert agent.model == 'gpt-4'
    assert agent.name == 'Test Assistant'

def test_thread_creation(mock_openai):
    session = Session()
    agent = AssistantAgent('test_assistant', session)

    thread_id = agent.create_thread()
    assert thread_id == 'test_thread'
    assert session.thread_id == 'test_thread'

def test_run_recording(mock_openai):
    session = Session()
    agent = AssistantAgent('test_assistant', session)

    thread_id = agent.create_thread()
    result = agent.run(thread_id)

    # Verify LLMEvent was recorded
    assert session.event_counts['llms'] > 0
