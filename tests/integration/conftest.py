import pytest

import agentops
from tests.fixtures.providers import (
    ai21_async_client,
    ai21_client,
    ai21_test_messages,
    anthropic_client,
    cohere_client,
    groq_client,
    litellm_client,
    mistral_client,
    openai_client,
    test_messages,
)
from tests.fixtures.vcr import vcr_config


@pytest.fixture
def agentops_init():
    agentops.init(auto_start_session=False)
    yield


@pytest.fixture
def agentops_session(agentops_init):
    session = agentops.start_session()

    assert session, "Failed agentops.start_session() returned None."

    yield session

    agentops.end_all_sessions()
