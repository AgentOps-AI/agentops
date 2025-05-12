import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from openai import OpenAI, BadRequestError

from agentops.sdk.decorators import session, operation

pytestmark = [pytest.mark.vcr]


@operation
async def make_llm_call(client, mock_response=None):
    """Make an LLM call and return the response"""
    if mock_response:
        return mock_response
    response = await client.chat.completions.create(
        model="gpt-3.5-turbo", messages=[{"role": "user", "content": "Write a one-line joke"}]
    )
    return response


@session
async def test_session_llm_tracking(openai_client, mock_response):
    """Test that LLM calls are tracked in session context"""
    try:
        response = await make_llm_call(openai_client, mock_response)
        assert response.choices[0].message.content is not None
    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")


@pytest.mark.asyncio
async def test_multiple_sessions():
    """Test concurrent sessions track LLM calls independently"""
    mock_client = MagicMock(spec=OpenAI)
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Test response"))]

    async def mock_create(**kwargs):
        return mock_response

    mock_client.chat.completions.create = AsyncMock(side_effect=mock_create)

    async def run_session(prompt: str):
        @session
        async def session_workflow():
            response = await mock_client.chat.completions.create(
                model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}]
            )
            return response

        return await session_workflow()

    # Run multiple sessions concurrently
    sessions = await asyncio.gather(
        run_session("Tell a joke"), run_session("Write a haiku"), run_session("Define OpenTelemetry")
    )

    # Verify each session completed successfully
    for response in sessions:
        assert response.choices[0].message.content is not None

    # Verify the mock was called the correct number of times
    assert mock_client.chat.completions.create.call_count == 3


@pytest.mark.asyncio
async def test_error_handling():
    """Test that errors are tracked in session context"""
    mock_client = MagicMock(spec=OpenAI)
    mock_client.chat.completions.create = AsyncMock(side_effect=BadRequestError("Invalid model"))

    @session
    async def error_session():
        with pytest.raises(BadRequestError) as exc_info:
            await mock_client.chat.completions.create(
                model="invalid-model", messages=[{"role": "user", "content": "test"}]
            )
        assert "Invalid model" in str(exc_info.value)

    await error_session()
