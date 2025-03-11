import asyncio
import logging
import pytest
from .conftest import (
    get_api_requests, 
    get_otel_requests, 
    assert_otel_requests_are_unique, 
    assert_instrumentation_is_loaded, 
)

import anthropic
import agentops

pytestmark = [pytest.mark.vcr]


MODEL = "claude-3-haiku-20240307"


@pytest.mark.asyncio
async def test_instrumentation_is_loaded():
    assert_instrumentation_is_loaded("anthropic")


@pytest.mark.asyncio
async def test_anthropic_completion_async_basic(vcr):
    """Test basic functionality of Anthropic Claude completion"""
    
    agentops.init()
    client = anthropic.AsyncAnthropic()
    response = await client.messages.create(
        model=MODEL,
        messages=[{"role": "user", "content": "Write a one-line joke"}],
        max_tokens=1000
    )
    agentops.end_session("Succeeded")

    req_api = get_api_requests(vcr)
    assert len(req_api) == 1, f"Expected 1 API request got {len(req_api)}"
    
    req_otel = get_otel_requests(vcr)
    assert len(req_otel) == 1, f"Expected 1 OTEL request got {len(req_otel)}"
    assert_otel_requests_are_unique(vcr)


@pytest.mark.asyncio
async def test_anthropic_system_prompt(vcr):
    """Test Anthropic with system prompt"""
    
    agentops.init()
    client = anthropic.AsyncAnthropic()
    response = await client.messages.create(
        model=MODEL,
        system="You are a helpful assistant",
        messages=[
            {"role": "user", "content": "Tell me about AI"}
        ],
        max_tokens=1000
    )
    agentops.end_session("Succeeded")

    req_api = get_api_requests(vcr)
    assert len(req_api) == 1, f"Expected 1 API request got {len(req_api)}"
    
    req_otel = get_otel_requests(vcr)
    assert len(req_otel) == 1, f"Expected 1 OTEL request got {len(req_otel)}"
    assert_otel_requests_are_unique(vcr)


@pytest.mark.asyncio
async def test_anthropic_completion_async_multiple(vcr):
    """Test multiple Anthropic completions"""
    
    async def run_session(prompt: str):
        client = anthropic.AsyncAnthropic()
        await client.messages.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000
        )

    agentops.init()
    await asyncio.gather(
        run_session("Tell a joke"),
        run_session("Write a haiku"),
        run_session("Define AI")
    )
    agentops.end_session("Succeeded")

    req_api = get_api_requests(vcr)
    assert len(req_api) == 1, f"Expected 1 API request got {len(req_api)}"
    
    req_otel = get_otel_requests(vcr)
    assert len(req_otel) == 3, f"Expected 3 OTEL requests got {len(req_otel)}"
    assert_otel_requests_are_unique(vcr)


@pytest.mark.asyncio
async def test_anthropic_completion_async_invalid_model(vcr):
    """Test error handling in Anthropic completion"""
    agentops.init()
    
    try:
        client = anthropic.AsyncAnthropic()
        with pytest.raises(anthropic.NotFoundError):
            # Use an invalid model to guarantee an error
            await client.messages.create(
                model="invalid-model",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1000
            )
    finally:
        agentops.end_session("Failed")

    req_api = get_api_requests(vcr)
    assert len(req_api) == 1, f"Expected 1 API request got {len(req_api)}"
    
    req_otel = get_otel_requests(vcr)
    assert len(req_otel) == 1, f"Expected 1 OTEL request got {len(req_otel)}"
    assert_otel_requests_are_unique(vcr)