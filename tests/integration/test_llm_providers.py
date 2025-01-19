import asyncio
from typing import Any, Dict, List
import json

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
        "gemini": lambda chunk: chunk.text if hasattr(chunk, "text") else None,
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
def test_openai_provider(openai_client, test_messages: List[Dict[str, Any]]):
    """Test OpenAI provider integration."""
    # Sync completion
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=test_messages,
        temperature=0.5,
    )
    assert response.choices[0].message.content

    # Stream completion
    stream = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=test_messages,
        temperature=0.5,
        stream=True,
    )
    content = collect_stream_content(stream, "openai")
    assert len(content) > 0


## Assistants API Tests
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

    while run.status not in ["completed", "failed"]:
        run = openai_client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

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
def test_anthropic_provider(anthropic_client):
    """Test Anthropic provider integration."""
    # Sync completion
    response = anthropic_client.messages.create(
        max_tokens=1024,
        model="claude-3-5-sonnet-latest",
        messages=[{"role": "user", "content": "Write a short greeting."}],
        system="You are a helpful assistant.",
    )
    assert response.content[0].text

    # Stream completion
    stream = anthropic_client.messages.create(
        max_tokens=1024,
        model="claude-3-5-sonnet-latest",
        messages=[{"role": "user", "content": "Write a short greeting."}],
        stream=True,
    )
    content = collect_stream_content(stream, "anthropic")
    assert len(content) > 0


# AI21 Tests
@pytest.mark.vcr()
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
@pytest.mark.vcr()
def test_cohere_provider(cohere_client):
    """Test Cohere provider integration."""
    # Sync chat
    response = cohere_client.chat(message="Say hello in spanish")
    assert response.text

    # Stream chat
    stream = cohere_client.chat_stream(message="Say hello in spanish")
    content = collect_stream_content(stream, "cohere")
    assert len(content) > 0


# Gemini Tests
@pytest.mark.vcr()
def test_gemini_provider(gemini_client, test_messages):
    """Test Gemini provider integration."""
    # Convert messages to Gemini format
    gemini_messages = []
    for msg in test_messages:
        if msg["role"] != "system":  # Gemini doesn't support system messages directly
            gemini_messages.append(msg["content"])
    
    # Sync completion
    response = gemini_client.generate_content(gemini_messages)
    assert response.text
    
    # Stream completion
    stream = gemini_client.generate_content(
        gemini_messages,
        stream=True
    )
    
    content = collect_stream_content(stream, "gemini")
    assert len(content) > 0
    
    # Test async completion
    async def async_test():
        response = await gemini_client.generate_content_async(gemini_messages)
        return response
    
    async_response = asyncio.run(async_test())
    assert async_response.text


# Groq Tests
@pytest.mark.vcr()
def test_groq_provider(groq_client, test_messages: List[Dict[str, Any]]):
    """Test Groq provider integration."""
    # Sync completion
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=test_messages,
    )
    assert response.choices[0].message.content

    # Stream completion
    stream = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=test_messages,
        stream=True,
    )
    content = collect_stream_content(stream, "groq")
    assert len(content) > 0


# Mistral Tests
@pytest.mark.vcr()
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
@pytest.mark.vcr()
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
        model="openai/gpt-4o-mini",
        messages=test_messages,
        stream=True,
    )
    content = collect_stream_content(stream_response, "litellm")
    assert len(content) > 0

    # Async completion
    async def async_test():
        async_response = await litellm_client.acompletion(
            model="anthropic/claude-3-5-sonnet-latest",
            messages=test_messages,
        )
        return async_response

    async_response = asyncio.run(async_test())
    assert async_response.choices[0].message.content


# Ollama Tests
@pytest.mark.vcr()
def test_ollama_provider(test_messages: List[Dict[str, Any]]):
    """Test Ollama provider integration."""
    import ollama
    from ollama import AsyncClient

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


# TaskWeaver Tests
@pytest.mark.vcr()
def test_taskweaver_provider(taskweaver_client, test_messages):
    """Test TaskWeaver provider integration."""
    # Test with code execution messages
    code_messages = [
        {"role": "system", "content": "You are a Python coding assistant."},
        {"role": "user", "content": "Write a function to calculate factorial. Answer in the JSON format."}
    ]
    
    response = taskweaver_client.chat_completion(
        messages=code_messages,
        temperature=0,
        max_tokens=200,
        top_p=1.0,
    )

    assert isinstance(response, dict)
    assert "content" in response
    
    # Convert 'content' from string to dictionary
    content = json.loads(response["content"])

    assert "function" in content

    assert "name" in content["function"]
    assert "description" in content["function"]
    assert "parameters" in content["function"]
    assert "returns" in content["function"]
    assert "code" in content["function"]

    assert "def factorial" in content["function"]["code"]
