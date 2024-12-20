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
import os
import asyncio
import uuid
import random
from dotenv import load_dotenv
import agentops
from anthropic import Anthropic
from agentops import Client
from agentops.llms.providers.anthropic import AnthropicProvider

# Setup environment and API keys
load_dotenv()

# Initialize clients with explicit API key
anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

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


async def generate_message(provider, personality, health):
    """Generate a Titan status message using the Anthropic API."""
    prompt = f"""You are a Titan from Titanfall. Your personality is: {personality}
    Your current health status is: {health}

    Generate a short status report (2-3 sentences) that reflects both your personality and current health status.
    Keep the tone consistent with a military combat AI but influenced by your unique personality."""

    messages = [{"role": "user", "content": prompt}]

    try:
        async with provider.create_stream_async(
            max_tokens=1024,
            model="claude-3-sonnet-20240229",
            messages=messages,
            stream=True
        ) as stream:
            message = ""
            async for text in stream.text_stream:
                print(text, end="", flush=True)
                message += text
            print()  # Add newline after message
            return message
    except Exception as e:
        print(f"Error generating message: {e}")
        return "Error: Unable to generate Titan status report."


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

