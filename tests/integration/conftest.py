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
def agentops_session():
    agentops.start_session()

    yield

    agentops.end_all_sessions()
