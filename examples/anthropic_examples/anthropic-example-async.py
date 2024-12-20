#!/usr/bin/env python
# coding: utf-8

"""
Anthropic Async Example

Anthropic supports both sync and async streaming! This example demonstrates async streaming
with a program called "Titan Support Protocol." The program assigns a personality type
to a mech and generates messages based on the Titan's health status, while concurrently
generating verification UUIDs.
"""

# Import required libraries
import asyncio
import os
import random
import uuid
from dotenv import load_dotenv
import agentops
from anthropic import Anthropic, AsyncAnthropic
from agentops import Client
from agentops.llms.providers.anthropic import AnthropicProvider

# Setup environment and API keys
load_dotenv()
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
if not anthropic_api_key:
    raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

# Initialize clients with explicit API key
anthropic_client = Anthropic(api_key=anthropic_api_key)
async_anthropic_client = AsyncAnthropic(api_key=anthropic_api_key)

# Initialize AgentOps client
ao_client = Client()
ao_client.configure(api_key=os.getenv("AGENTOPS_API_KEY"), default_tags=["anthropic-async"])
ao_client.initialize()

"""
Titan Personalities:
- Legion: Relentless and heavy-hitting, embodies brute strength
- Northstar: Precise and agile sniper, excels in long-range combat
- Ronin: Swift and aggressive melee specialist, close-quarters combat expert
"""

# Define personality presets
TitanPersonality = [
    "Legion is a relentless and heavy-hitting Titan that embodies brute strength and defensive firepower. He speaks bluntly.",
    "Northstar is a precise and agile sniper that excels in long-range combat and flight. He speaks with an edge of coolness to him",
    "Ronin is a swift and aggressive melee specialist who thrives on close-quarters hit-and-run tactics. He talks like a Samurai might.",
]

# Define health status presets
TitanHealth = [
    "Fully functional",
    "Slightly Damaged",
    "Moderate Damage",
    "Considerable Damage",
    "Near Destruction",
]

# Generate random personality and health status
Personality = random.choice(TitanPersonality)
Health = random.choice(TitanHealth)


async def generate_message(personality, health_status):
    """Generate a message based on personality and health status."""
    # Create provider with explicit sync and async clients
    provider = AnthropicProvider(
        client=anthropic_client,
        async_client=async_anthropic_client
    )

    prompt = f"""Given the following Titan personality and health status, generate a short combat log message (1-2 sentences):
    Personality: {personality}
    Health Status: {health_status}

    The message should reflect both the personality and current health status."""

    messages = [{"role": "user", "content": prompt}]

    stream = await provider.create_stream_async(
        messages=messages,
        model="claude-3-opus-20240229",
        max_tokens=1024,
        stream=True
    )

    async with stream:
        async for text in stream.text_stream:
            print(text, end="", flush=True)
        print()

    return "Message generation complete"


async def generate_uuids():
    """Generate 4 UUIDs for verification matrix."""
    return [str(uuid.uuid4()) for _ in range(4)]


async def main():
    """Main function to run the Titan Support Protocol."""
    print("Initializing Titan Support Protocol...\n")

    # Display selected personality and health status
    print(f"Personality: {Personality}")
    print(f"Health Status: {Health}\n")

    print("Combat log incoming from encrypted area")

    # Generate message and UUIDs concurrently
    titan_message, uuids = await asyncio.gather(
        generate_message(Personality, Health),
        generate_uuids()
    )

    # Print verification matrix
    if uuids:
        print("\nVerification Matrix:")
        for uuid in uuids:
            print(f"- {uuid}")


if __name__ == "__main__":
    # Run the main function using asyncio
    asyncio.run(main())
    # End the AgentOps session with success status
    ao_client.end_session("Success")

