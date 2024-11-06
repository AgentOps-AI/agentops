import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

import litellm  # litellm, openai need to be imported before agentops.init
import openai
import pytest

import agentops

os.environ["VCR_TURN_OFF"] = "true"


if TYPE_CHECKING:
    from pytest_mock import MockerFixture

try:
    import pytest_vcr  # noqa: F401
except ImportError:
    raise RuntimeError("Please install pytest-vcr to run this test")

agentops.logger.setLevel(logging.DEBUG)


@pytest.fixture(scope="session", autouse=True)
def agentops_init():
    agentops.init(api_key=os.getenv("AGENTOPS_API_KEY", ""))


@pytest.fixture
def agentops_client():
    return agentops.Client()


@pytest.fixture(scope="session")
def litellm_client():
    return litellm


@pytest.fixture(scope="session")
def openai_client():
    return openai.Client()


@pytest.fixture(scope="module")
def vcr(vcr):
    return vcr


@pytest.fixture(scope="module")
def vcr_config():
    vcr_cassettes = Path(__file__).parent / "fixtures" / "vcr_cassettes" / __name__
    vcr_cassettes.mkdir(parents=True, exist_ok=True)
    return {
        "serializer": "yaml",
        "cassette_library_dir": str(vcr_cassettes),
        # Enhanced header filtering using tuples for replacement values
        "filter_headers": [
            # Auth headers with REDACTED values
            ("authorization", "REDACTED"),
            ("api-key", "REDACTED"),
            ("x-api-key", "REDACTED"),
            ("X-Agentops-Api-Key", "REDACTED"),
            ("openai-organization", "REDACTED"),
            # User identifiers
            ("user-agent", "REDACTED"),
            # Cookie related - remove completely
            ("cookie", "REDACTED"),  # Request cookies
            ("set-cookie", "REDACTED"),  # Response cookies (both cases)
            ("Set-Cookie", "REDACTED"),
            ("Cookie", "REDACTED"),
            # IP addresses and other sensitive headers
            ("x-forwarded-for", "REDACTED"),
            ("x-real-ip", "REDACTED"),
            ("request-id", "REDACTED"),
        ],
        # Other settings remain the same
        "match_on": ["uri", "method", "body", "query"],
        "decode_compressed_response": True,
        "record_on_exception": False,
        "record_mode": "once",
        "ignore_hosts": ["pypi.org", "files.pythonhosted.org"],
    }


@pytest.fixture
def llm_event_spy(agentops_client, mocker: "MockerFixture"):
    """Fixture that provides spies on both providers' response handling"""
    from agentops.llms.litellm import LiteLLMProvider
    from agentops.llms.openai import OpenAiProvider

    return {
        "litellm": mocker.spy(LiteLLMProvider(agentops_client), "handle_response"),
        "openai": mocker.spy(OpenAiProvider(agentops_client), "handle_response"),
    }


@pytest.mark.vcr
def test_openai_litellm_tango(llm_event_spy, openai_client, litellm_client):
    """Test that LiteLLM integration does not break OpenAI from sending events"""
    message = [{"role": "user", "content": "Write a 3 word sentence."}]

    litellm_client.completion(
        model="claude-3-sonnet-20240229", messages=message, temperature=0
    )

    assert llm_event_spy["litellm"].call_count == 1

    openai_client.chat.completions.create(
        model="gpt-4", messages=message, temperature=0
    )

    assert llm_event_spy["openai"].call_count == 1
