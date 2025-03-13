import asyncio
from uuid import uuid4

import openai
import pytest
from opentelemetry import trace

from agentops import Config, Session

pytestmark = [pytest.mark.vcr]


@pytest.mark.asyncio
async def test_session_llm_tracking(agentops_session):
    """Test that LLM calls are tracked in session context"""

    try:
        client = openai.AsyncOpenAI()
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo", messages=[{"role": "user", "content": "Write a one-line joke"}]
        )

        # Verify session tracking
        assert session.event_counts["llms"] == 1
        assert session.event_counts["errors"] == 0
        assert response.choices[0].message.content is not None

    finally:
        session.end("SUCCEEDED")


# @pytest.mark.asyncio
# async def test_multiple_sessions():
#     """Test concurrent sessions track LLM calls independently"""
#     async def run_session(prompt: str):
#         session = Session(session_id=uuid4())
#
#         client = openai.AsyncOpenAI()
#         await client.chat.completions.create(
#             model="gpt-3.5-turbo",
#             messages=[{"role": "user", "content": prompt}]
#         )
#
#         return session
#
#     # Run multiple sessions concurrently
#     sessions = await asyncio.gather(
#         run_session("Tell a joke"),
#         run_session("Write a haiku"),
#         run_session("Define OpenTelemetry")
#     )
#
#     # Verify each session tracked its calls independently
#     for session in sessions:
#         assert session.event_counts["llms"] == 1
#         assert session.event_counts["errors"] == 0
#         session.end("SUCCEEDED")
#
# @pytest.mark.asyncio
# async def test_error_handling():
#     """Test that errors are tracked in session context"""
#     session = Session(session_id=uuid4())
#
#     try:
#         client = openai.AsyncOpenAI()
#         with pytest.raises(openai.BadRequestError):
#             # Use an invalid model to guarantee an error
#             await client.chat.completions.create(
#                 model="invalid-model",
#                 messages=[{"role": "user", "content": "test"}]
#             )
#
#         # Verify error tracking
#         assert session.event_counts["errors"] == 1
#         assert session.state == "FAILED"
#
#     finally:
#         if session.is_running:
#             session.end("FAILED")
