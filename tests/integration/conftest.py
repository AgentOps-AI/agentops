
"""
Integration Tests
-----------------

We want to minimize the amount of patching we do to `agentops` and instead run as
much of these tests as possible with real-world implementations. 

VCR is used to cache data requests made to external services. 
"""
import os
import pytest

# import agentops
# from tests.fixtures.providers import (
#     ai21_async_client,
#     ai21_client,
#     ai21_test_messages,
#     anthropic_client,
#     cohere_client,
#     groq_client,
#     litellm_client,
#     mistral_client,
#     openai_client,
#     test_messages,
# )
from tests.fixtures.vcr import vcr_config


# @pytest.fixture
# def agentops_session():
#     agentops.start_session()

#     yield

#     agentops.end_all_sessions()

OPENAI_MODEL_NAMES = [
    "o3-mini",
    "o3-mini-2025-01-31",
    "o1",
    "o1-2024-12-17",
    "o1-preview",
    "o1-preview-2024-09-12",
    "o1-mini",
    "o1-mini-2024-09-12",
    "gpt-4o",
    "gpt-4o-2024-11-20",
    "gpt-4o-2024-08-06",
    "gpt-4o-2024-05-13",
    "gpt-4o-audio-preview",
    "gpt-4o-audio-preview-2024-10-01",
    "gpt-4o-audio-preview-2024-12-17",
    "gpt-4o-mini-audio-preview",
    "gpt-4o-mini-audio-preview-2024-12-17",
    "chatgpt-4o-latest",
    "gpt-4o-mini",
    "gpt-4o-mini-2024-07-18",
    "gpt-4-turbo",
    "gpt-4-turbo-2024-04-09",
    "gpt-4-0125-preview",
    "gpt-4-turbo-preview",
    "gpt-4-1106-preview",
    "gpt-4-vision-preview",
    "gpt-4",
    "gpt-4-0314",
    "gpt-4-0613",
    "gpt-4-32k",
    "gpt-4-32k-0314",
    "gpt-4-32k-0613",
    "gpt-3.5-turbo",
    "gpt-3.5-turbo-16k",
    "gpt-3.5-turbo-0301",
    "gpt-3.5-turbo-0613",
    "gpt-3.5-turbo-1106",
    "gpt-3.5-turbo-0125",
    "gpt-3.5-turbo-16k-0613",
    "computer-use-preview-2025-02-04",
]


def agentops_config():
    """Get the agentops configuration for testing"""
    import agentops  # lazy load so we can still modify ENV
    return agentops.Client()._config


def _get_requests_for_domain(vcr, domain: str) -> list:
    """Get requests for a specific domain from the VCR cassette"""
    return [req for req in vcr.requests if req.uri.startswith(domain)]


def get_api_requests(vcr):
    """Get the API requests from the VCR cassette
    
    Note: Due to AgentOps batching mechanism, we typically expect to see only one AgentOps API request
    regardless of the number of agents or operations performed during a session.
    """
    config = agentops_config()
    return _get_requests_for_domain(vcr, config.endpoint)


def get_otel_requests(vcr):
    """Get the OpenTelemetry requests from the VCR cassette"""
    config = agentops_config()
    return _get_requests_for_domain(vcr, config.exporter_endpoint)


def assert_otel_requests_are_unique(vcr):
    """Assert that the OpenTelemetry requests are unique"""
    otel_requests = get_otel_requests(vcr)
    bodys = [req.body for req in otel_requests]
    assert len(bodys) == len(set(bodys)), "All OpenTelemetry requests are not unique"


def assert_instrumentation_is_loaded(package_name: str):
    """Ensure that the AgentOps instrumentation is loaded."""
    from agentops.instrumentation import available_instrumentors
    import agentops.instrumentation
    
    loader = [l for l in available_instrumentors if l.provider_import_name == package_name][0]
    assert loader.get_instance() in agentops.instrumentation._active_instrumentors, \
        f"AgentOps instrumentation is not loaded for {package_name}"

