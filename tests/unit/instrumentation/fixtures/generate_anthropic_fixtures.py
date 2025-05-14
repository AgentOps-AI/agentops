import os
import json
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic

# Load environment variables
load_dotenv()

# Initialize Anthropic client
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

client = Anthropic()

# Directory to save fixtures
FIXTURES_DIR = Path(__file__).parent


def save_fixture(data, filename):
    """Save response data as a JSON fixture"""
    filepath = FIXTURES_DIR / filename
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved fixture: {filepath}")


def generate_fixtures():
    """Generate various Anthropic API response fixtures"""

    # 1. Basic message completion
    message_response = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=100,
        messages=[{"role": "user", "content": "What is the capital of France?"}],
    )
    save_fixture(message_response.model_dump(), "anthropic_message.json")

    # 2. Message with system prompt
    system_message_response = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=100,
        system="You are a helpful assistant that provides concise answers.",
        messages=[{"role": "user", "content": "What is Python?"}],
    )
    save_fixture(system_message_response.model_dump(), "anthropic_system_message.json")

    # 3. Multi-turn conversation
    conversation_response = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=100,
        messages=[
            {"role": "user", "content": "Let's plan a trip."},
            {"role": "assistant", "content": "I'd be happy to help plan a trip. Where would you like to go?"},
            {"role": "user", "content": "I'm thinking about visiting Japan."},
        ],
    )
    save_fixture(conversation_response.model_dump(), "anthropic_conversation.json")

    # 4. Streaming response
    stream_messages = []
    stream = client.messages.stream(
        model="claude-3-opus-20240229",
        max_tokens=100,
        messages=[{"role": "user", "content": "Count from 1 to 5 slowly."}],
    )

    with stream as response:
        for text in response.text_stream:
            stream_messages.append({"type": "text", "content": text})

        # Get the final message after streaming is complete
        final_message = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=100,
            messages=[{"role": "user", "content": "Count from 1 to 5 slowly."}],
        )

    save_fixture({"messages": stream_messages, "final_message": final_message.model_dump()}, "anthropic_stream.json")


if __name__ == "__main__":
    generate_fixtures()
