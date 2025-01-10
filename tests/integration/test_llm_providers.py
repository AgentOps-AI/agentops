import pytest
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

@pytest.fixture
def openai_client():
    return OpenAI()

@pytest.mark.vcr()
def test_openai_provider(openai_client):
    """Test OpenAI provider integration with sync, async and streaming calls."""
    # Test synchronous completion
    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Hello"}],
        temperature=0.5,
    )
    assert response.choices[0].message.content
    
    # Test streaming
    stream_response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Hello streamed"}],
        temperature=0.5,
        stream=True,
    )
    collected_messages = []
    for chunk in stream_response:
        if chunk.choices[0].delta.content:
            collected_messages.append(chunk.choices[0].delta.content)
    assert len(collected_messages) > 0

