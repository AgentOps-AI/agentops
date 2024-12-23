from typing import TYPE_CHECKING
import vcr
from vcr.record_mode import RecordMode
import pytest
import os
from collections import defaultdict

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture(scope="function")
def llm_event_spy(agentops_client, mocker: "MockerFixture"):
    """Fixture that provides spies on both providers' response handling"""
    from agentops.llms.providers.anthropic import AnthropicProvider
    from agentops.llms.providers.litellm import LiteLLMProvider
    from agentops.llms.providers.openai import OpenAiProvider

    return {
        "litellm": mocker.spy(LiteLLMProvider(agentops_client), "handle_response"),
        "openai": mocker.spy(OpenAiProvider(agentops_client), "handle_response"),
        "anthropic": mocker.spy(AnthropicProvider(agentops_client), "handle_response"),
    }
