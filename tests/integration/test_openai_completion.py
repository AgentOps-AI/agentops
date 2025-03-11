import asyncio
import logging
import pytest
import pydantic
from .conftest import (
    get_api_requests, 
    get_otel_requests, 
    assert_otel_requests_are_unique, 
    assert_instrumentation_is_loaded, 
)

import openai
import agentops

pytestmark = [pytest.mark.vcr]

MODEL = "gpt-3.5-turbo"


@pytest.mark.asyncio
async def test_instrumentation_is_loaded():
    assert_instrumentation_is_loaded("openai")


@pytest.mark.asyncio
async def test_openai_completion_async_basic(vcr):
    """Test basic functionality of OpenAI completion"""
    
    agentops.init()
    client = openai.AsyncOpenAI()
    response = await client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "Write a one-line joke"}]
    )
    agentops.end_session("Succeeded")

    req_api = get_api_requests(vcr)
    assert len(req_api) == 1, f"Expected 1 API request got {len(req_api)}"
    
    req_otel = get_otel_requests(vcr)
    assert len(req_otel) == 1, f"Expected 1 OTEL request got {len(req_otel)}"
    assert_otel_requests_are_unique(vcr)


@pytest.mark.asyncio
async def test_openai_completion_async_tool_use(vcr):
    """Test basic functionality of OpenAI completion"""
    
    agentops.init()
    client = openai.AsyncOpenAI()
    response = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": "How's the weather in San Francisco?"}, 
        ], 
        tools=[{
            "type": "function",
            "function": {
                "name": "get_current_weather",
                "description": "Get the current weather in a given location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA"
                        },
                    },
                    "required": ["location"]
                }
            }
        }], 
        tool_choice="required", 
        parallel_tool_calls=True,  # default value
    )
    agentops.end_session("Succeeded")
    
    req_api = get_api_requests(vcr)
    assert len(req_api) == 1, f"Expected 1 API request got {len(req_api)}"
    
    req_otel = get_otel_requests(vcr)
    assert len(req_otel) == 1, f"Expected 1 OTEL request got {len(req_otel)}"
    assert_otel_requests_are_unique(vcr)
    # TODO verify tool call is in the request


@pytest.mark.asyncio
async def test_openai_completion_format_json(vcr):
    """Test response formats in JSON from OpenAI completion"""
    
    agentops.init()
    client = openai.AsyncOpenAI()
    response = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant that responds only in JSON format."},
            {"role": "user", "content": "Generate a list of 3 book recommendations with title, author and year"}
        ],
        response_format={"type": "json_object"}
    )
    agentops.end_session("Succeeded")
    
    req_api = get_api_requests(vcr)
    assert len(req_api) == 1, f"Expected 1 API request got {len(req_api)}"
    
    req_otel = get_otel_requests(vcr)
    assert len(req_otel) == 1, f"Expected 1 OTEL request got {len(req_otel)}"
    assert_otel_requests_are_unique(vcr)


# @pytest.mark.asyncio
# async def test_openai_completion_format_pydantic(vcr):
#     """Test response formats in JSON with Pydantic schema from OpenAI completion"""
    
#     class BookRecommendation(pydantic.BaseModel):
#         title: str = pydantic.Field(description="Title of the book")
#         author: str = pydantic.Field(description="Author of the book")
#         year: int = pydantic.Field(description="Publication year of the book")
    
#     class BookRecommendations(pydantic.BaseModel):
#         recommendations: list[BookRecommendation] = pydantic.Field(
#             description="List of book recommendations"
#         )
    
#     agentops.init()
#     client = openai.AsyncOpenAI()
#     response = await client.chat.completions.create(
#         model=MODEL,
#         messages=[
#             {"role": "system", "content": "You are a helpful assistant that responds in structured JSON."},
#             {"role": "user", "content": "Generate a list of 3 book recommendations with title, author and year"}
#         ],
#         response_format={"type": "json_object"},
#         json_schema=BookRecommendations.model_json_schema()
#     )
#     agentops.end_session("Succeeded")
    
#     req_api = get_api_requests(vcr)
#     assert len(req_api) == 1, f"Expected 1 API request got {len(req_api)}"
    
#     req_otel = get_otel_requests(vcr)
#     assert len(req_otel) == 1, f"Expected 1 OTEL request got {len(req_otel)}"
#     assert_otel_requests_are_unique(vcr)


@pytest.mark.asyncio
async def test_openai_completion_async_multiple(vcr):
    """Test multiple OpenAI completions"""
    
    async def run_session(prompt: str):
        client = openai.AsyncOpenAI()
        await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        # TODO does agentops expect us to call something between requests?

    agentops.init()
    await asyncio.gather(
        run_session("Tell a joke"),
        run_session("Write a haiku"),
        run_session("Define OpenTelemetry")
    )
    agentops.end_session("Succeeded")

    req_api = get_api_requests(vcr)
    assert len(req_api) == 1, f"Expected 1 API request got {len(req_api)}"
    
    req_otel = get_otel_requests(vcr)
    assert len(req_otel) == 3, f"Expected 3 OTEL requests got {len(req_otel)}"
    assert_otel_requests_are_unique(vcr)
    # TODO verify that each session tracks its own requests


@pytest.mark.asyncio
async def test_openai_completion_async_invalid_model(vcr):
    """Test error handling in OpenAI completion"""
    agentops.init()
    
    try:
        client = openai.AsyncOpenAI()
        with pytest.raises(openai.NotFoundError):
            # Use an invalid model to guarantee an error
            await client.chat.completions.create(
                model="invalid-model",
                messages=[{"role": "user", "content": "test"}]
            )
    finally:
        agentops.end_session("Failed")

    req_api = get_api_requests(vcr)
    assert len(req_api) == 1, f"Expected 1 API request got {len(req_api)}"
    
    req_otel = get_otel_requests(vcr)
    assert len(req_otel) == 1, f"Expected 1 OTEL request got {len(req_otel)}"
    assert_otel_requests_are_unique(vcr)
    # TODO verify that the error is captured correctly

