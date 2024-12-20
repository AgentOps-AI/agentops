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
from anthropic import Anthropic
from agentops import Client
from agentops.llms.providers.anthropic import AnthropicProvider

# Setup environment and API keys
load_dotenv()
anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
ao_client = Client(api_key=os.getenv("AGENTOPS_API_KEY"), default_tags=["anthropic-async"])

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


async def generate_message(provider, personality, health_status):
    """Generate a message from the Titan based on personality and health status."""
    messages = [
        {
            "role": "user",
            "content": f"You are a Titan mech with this personality: {personality}. Your health status is: {health_status}. Generate a status report in your personality's voice. Keep it under 100 words.",
        }
    ]

    message = ""
    stream = await provider.create_stream_async(
        max_tokens=1024,
        model="claude-3-sonnet-20240229",
        messages=messages,
        stream=True,
    )
    async with stream:
        async for text in stream.text_stream:
            message += text
            print(text, end="", flush=True)
        print()

    return message


async def generate_uuids():
    """Generate 4 UUIDs for verification matrix."""
    return [str(uuid.uuid4()) for _ in range(4)]


async def main():
    """Main function to run the Titan Support Protocol."""
    print("Initializing Titan Support Protocol...\n")
    print("Personality:", Personality)
    print("Health Status:", Health)
    print("\nCombat log incoming from encrypted area")

    provider = AnthropicProvider(client=ao_client, async_client=anthropic_client)
    # Run both functions concurrently and properly unpack results
    titan_message, uuids = await asyncio.gather(
        generate_message(provider, Personality, Health),
        generate_uuids(),
    )

    print("\nVerification matrix activated:")
    for u in uuids:
        print(u)

    print("\nTitan Message:")
    print(titan_message)


if __name__ == "__main__":
    # Run the main function using asyncio
    asyncio.run(main())
    # End the AgentOps session with success status
    ao_client.end_session("Success")

