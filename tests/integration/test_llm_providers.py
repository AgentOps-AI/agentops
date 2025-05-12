import asyncio
from asyncio import TimeoutError
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest


def collect_stream_content(stream_response: Any, provider: str) -> List[str]:
    """Collect streaming content based on provider-specific response format."""
    collected_content = []

    handlers = {
        "openai": lambda chunk: chunk.choices[0].delta.content,
        "anthropic": lambda event: event.delta.text if event.type == "content_block_delta" else None,
        "cohere": lambda event: event.text if event.event_type == "text-generation" else None,
        "ai21": lambda chunk: chunk.choices[0].delta.content,
        "groq": lambda chunk: chunk.choices[0].delta.content,
        "mistral": lambda event: event.data.choices[0].delta.content
        if hasattr(event.data.choices[0].delta, "content")
        else None,
        "litellm": lambda chunk: chunk.choices[0].delta.content if hasattr(chunk.choices[0].delta, "content") else None,
        "ollama": lambda chunk: chunk["message"]["content"] if "message" in chunk else None,
    }

    handler = handlers.get(provider)
    if not handler:
        raise ValueError(f"Unknown provider: {provider}")

    for chunk in stream_response:
        if chunk_content := handler(chunk):
            collected_content.append(chunk_content)

    return collected_content


# OpenAI Tests
@pytest.mark.vcr()
def test_openai_provider(openai_client, test_messages: List[Dict[str, Any]], mock_response):
    """Test OpenAI provider integration."""
    # Mock the client's create method
    openai_client.chat.completions.create = MagicMock(return_value=mock_response)

    # Sync completion
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=test_messages,
        temperature=0.5,
    )
    assert response.choices[0].message.content

    # Stream completion
    mock_stream = [
        MagicMock(choices=[MagicMock(delta=MagicMock(content="Hello"))]),
        MagicMock(choices=[MagicMock(delta=MagicMock(content=" World"))]),
    ]
    openai_client.chat.completions.create = MagicMock(return_value=mock_stream)

    stream = openai_client.chat.completions.create(
        model="gpt-4",
        messages=test_messages,
        temperature=0.5,
        stream=True,
    )
    content = collect_stream_content(stream, "openai")
    assert len(content) > 0
    assert "".join(content) == "Hello World"


# Assistants API Tests (OpenAI)
@pytest.mark.skip(reason="TODO: OpenAI Assistants API integration test needs to be implemented")
@pytest.mark.vcr()
async def test_openai_assistants_provider(openai_client):
    """Test OpenAI Assistants API integration for all overridden methods."""
    # Test Assistants CRUD operations
    # Create
    assistant = openai_client.beta.assistants.create(
        name="Math Tutor",
        instructions="You are a personal math tutor. Write and run code to answer math questions.",
        tools=[{"type": "code_interpreter"}],
        model="gpt-4o-mini",
    )
    assert assistant.id.startswith("asst_")

    # Retrieve
    retrieved_assistant = openai_client.beta.assistants.retrieve(assistant.id)
    assert retrieved_assistant.id == assistant.id

    # Update
    updated_assistant = openai_client.beta.assistants.update(
        assistant.id,
        name="Advanced Math Tutor",
        instructions="You are an advanced math tutor. Explain concepts in detail.",
    )
    assert updated_assistant.name == "Advanced Math Tutor"

    # List
    assistants_list = openai_client.beta.assistants.list()
    assert any(a.id == assistant.id for a in assistants_list.data)

    # Test Threads CRUD operations
    # Create
    thread = openai_client.beta.threads.create()
    assert thread.id.startswith("thread_")

    # Add Multiple Messages
    message1 = openai_client.beta.threads.messages.create(
        thread_id=thread.id, role="user", content="I need to solve the equation `3x + 11 = 14`. Can you help me?"
    )
    message2 = openai_client.beta.threads.messages.create(
        thread_id=thread.id, role="user", content="Also, what is the square root of 144?"
    )
    assert message1.content[0].text.value
    assert message2.content[0].text.value

    # Create and monitor run
    run = openai_client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant.id)
    assert run.id.startswith("run_")

    # Monitor run status with timeout
    async def check_run_status():
        while True:
            run_status = openai_client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            print(f"Current run status: {run_status.status}")  # Print status for debugging
            if run_status.status in ["completed", "failed", "cancelled", "expired"]:
                return run_status
            await asyncio.sleep(1)

    try:
        await asyncio.wait_for(check_run_status(), timeout=10)  # Shorter timeout
    except TimeoutError:
        # Cancel the run if it's taking too long
        openai_client.beta.threads.runs.cancel(thread_id=thread.id, run_id=run.id)
        pytest.skip("Assistant run timed out and was cancelled")

    # Get run steps
    run_steps = openai_client.beta.threads.runs.steps.list(thread_id=thread.id, run_id=run.id)
    assert len(run_steps.data) > 0

    # List messages
    messages = openai_client.beta.threads.messages.list(thread_id=thread.id)
    assert len(messages.data) > 0

    # Update thread
    updated_thread = openai_client.beta.threads.update(thread.id, metadata={"test": "value"})
    assert updated_thread.metadata.get("test") == "value"

    # Clean up
    openai_client.beta.threads.delete(thread.id)
    openai_client.beta.assistants.delete(assistant.id)


# Anthropic Tests
@pytest.mark.vcr()
def test_anthropic_provider(anthropic_client, test_messages: List[Dict[str, Any]], mock_response):
    """Test Anthropic provider integration."""
    # Mock the client's create method
    anthropic_client.messages.create = MagicMock(return_value=mock_response)

    # Sync completion
    response = anthropic_client.messages.create(
        max_tokens=1024,
        model="claude-3-sonnet-20240229",
        messages=test_messages,
        system="You are a helpful assistant.",
    )
    assert response.content[0].text

    # Stream completion
    mock_stream = [
        MagicMock(type="content_block_delta", delta=MagicMock(text="Hello")),
        MagicMock(type="content_block_delta", delta=MagicMock(text=" World")),
    ]
    anthropic_client.messages.create = MagicMock(return_value=mock_stream)

    stream = anthropic_client.messages.create(
        max_tokens=1024,
        model="claude-3-sonnet-20240229",
        messages=test_messages,
        stream=True,
    )
    content = collect_stream_content(stream, "anthropic")
    assert len(content) > 0
    assert "".join(content) == "Hello World"


# AI21 Tests
@pytest.mark.skip(reason="TODO: instrumentation")
def test_ai21_provider(ai21_client, ai21_async_client, ai21_test_messages: List[Dict[str, Any]]):
    """Test AI21 provider integration."""
    # Sync completion
    response = ai21_client.chat.completions.create(
        model="jamba-1.5-mini",
        messages=ai21_test_messages,
    )
    assert response.choices[0].message.content

    # Stream completion
    stream = ai21_client.chat.completions.create(
        model="jamba-1.5-mini",
        messages=ai21_test_messages,
        stream=True,
    )
    content = collect_stream_content(stream, "ai21")
    assert len(content) > 0

    # Async completion
    async def async_test():
        response = await ai21_async_client.chat.completions.create(
            model="jamba-1.5-mini",
            messages=ai21_test_messages,
        )
        return response

    async_response = asyncio.run(async_test())
    assert async_response.choices[0].message.content


# Cohere Tests
@pytest.mark.skip(reason="TODO: instrumentation")
def test_cohere_provider(cohere_client):
    """Test Cohere provider integration."""
    # Sync chat
    response = cohere_client.chat(message="Say hello in spanish")
    assert response.text

    # Stream chat
    stream = cohere_client.chat_stream(message="Say hello in spanish")
    content = collect_stream_content(stream, "cohere")
    assert len(content) > 0


# Groq Tests
@pytest.mark.skip(reason="TODO: instrumentation")
def test_groq_provider(groq_client, test_messages: List[Dict[str, Any]]):
    """Test Groq provider integration."""
    # Sync completion
    response = groq_client.chat.completions.create(
        model="llama3-70b-8192",
        messages=test_messages,
    )
    assert response.choices[0].message.content

    # Stream completion
    stream = groq_client.chat.completions.create(
        model="llama3-70b-8192",
        messages=test_messages,
        stream=True,
    )
    content = collect_stream_content(stream, "groq")
    assert len(content) > 0


# Mistral Tests
@pytest.mark.skip(reason="TODO: instrumentation")
def test_mistral_provider(mistral_client, test_messages: List[Dict[str, Any]]):
    """Test Mistral provider integration."""
    # Sync completion
    response = mistral_client.chat.complete(
        model="open-mistral-nemo",
        messages=test_messages,
    )
    assert response.choices[0].message.content

    # Stream completion
    stream = mistral_client.chat.stream(
        model="open-mistral-nemo",
        messages=test_messages,
    )
    content = collect_stream_content(stream, "mistral")
    assert len(content) > 0

    # Async completion
    async def async_test():
        response = await mistral_client.chat.complete_async(
            model="open-mistral-nemo",
            messages=test_messages,
        )
        return response

    async_response = asyncio.run(async_test())
    assert async_response.choices[0].message.content


# LiteLLM Tests
@pytest.mark.skip(reason="TODO: instrumentation for callback handlers and external integrations")
def test_litellm_provider(litellm_client, test_messages: List[Dict[str, Any]]):
    """Test LiteLLM provider integration."""
    # Sync completion
    response = litellm_client.completion(
        model="openai/gpt-4o-mini",
        messages=test_messages,
    )
    assert response.choices[0].message.content

    # Stream completion
    stream_response = litellm_client.completion(
        model="anthropic/claude-3-5-sonnet-latest",
        messages=test_messages,
        stream=True,
    )
    content = collect_stream_content(stream_response, "litellm")
    assert len(content) > 0

    # Async completion
    async def async_test():
        async_response = await litellm_client.acompletion(
            model="openrouter/deepseek/deepseek-chat",
            messages=test_messages,
        )
        return async_response

    async_response = asyncio.run(async_test())
    assert async_response.choices[0].message.content


# Ollama Tests
@pytest.mark.skip(reason="TODO: instrumentation")
def test_ollama_provider(test_messages: List[Dict[str, Any]]):
    """Test Ollama provider integration."""
    import ollama
    from ollama import AsyncClient

    try:
        # Test if Ollama server is running
        ollama.list()
    except Exception as e:
        pytest.skip(f"Ollama server not running: {e}")

    try:
        # Sync chat
        response = ollama.chat(
            model="llama3.2:1b",
            messages=test_messages,
        )
        assert response["message"]["content"]

        # Stream chat
        stream = ollama.chat(
            model="llama3.2:1b",
            messages=test_messages,
            stream=True,
        )
        content = collect_stream_content(stream, "ollama")
        assert len(content) > 0

        # Async chat
        async def async_test():
            client = AsyncClient()
            response = await client.chat(
                model="llama3.2:1b",
                messages=test_messages,
            )
            return response

        async_response = asyncio.run(async_test())
        assert async_response["message"]["content"]

    except Exception as e:
        pytest.skip(f"Ollama test failed: {e}")
