import os
import pytest
from typing import Any, List
import litellm
from openai import OpenAI
from anthropic import Anthropic
from ai21 import AI21Client, AsyncAI21Client
from cohere import Client as CohereClient
from groq import Groq
from mistralai import Mistral
from ai21.models.chat import ChatMessage
from dotenv import load_dotenv

load_dotenv()

# Test messages for different providers
@pytest.fixture
def test_messages():
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Write a short greeting."}
    ]

@pytest.fixture
def ai21_test_messages():
    return [
        ChatMessage(content="You are an expert mathematician.", role="system"),
        ChatMessage(
            content="Write a summary of 5 lines on the Shockley diode equation.",
            role="user",
        ),
    ]

# Client fixtures
@pytest.fixture
def openai_client():
    """Initialize OpenAI client."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not found in environment variables")
    return OpenAI(api_key=api_key)

@pytest.fixture
def anthropic_client():
    """Initialize Anthropic client."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not found in environment variables")
    return Anthropic(api_key=api_key)

@pytest.fixture
def ai21_client():
    """Initialize AI21 sync client."""
    api_key = os.getenv("AI21_API_KEY")
    if not api_key:
        pytest.skip("AI21_API_KEY not found in environment variables")
    return AI21Client(api_key=api_key)

@pytest.fixture
def ai21_async_client():
    """Initialize AI21 async client."""
    api_key = os.getenv("AI21_API_KEY")
    if not api_key:
        pytest.skip("AI21_API_KEY not found in environment variables")
    return AsyncAI21Client(api_key=api_key)

@pytest.fixture
def cohere_client():
    """Initialize Cohere client."""
    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        pytest.skip("COHERE_API_KEY not found in environment variables")
    return CohereClient(api_key=api_key)

@pytest.fixture
def groq_client():
    """Initialize Groq client."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        pytest.skip("GROQ_API_KEY not found in environment variables")
    return Groq(api_key=api_key)

@pytest.fixture
def mistral_client():
    """Initialize Mistral client."""
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        pytest.skip("MISTRAL_API_KEY not found in environment variables")
    return Mistral(api_key=api_key)

@pytest.fixture
def litellm_client():
    """Initialize LiteLLM client."""
    return litellm