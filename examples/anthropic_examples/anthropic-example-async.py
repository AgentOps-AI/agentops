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
from anthropic import Anthropic
import agentops
from dotenv import load_dotenv
import os
import random
import asyncio
import uuid

# Setup environment and API keys
load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY") or "<your_anthropic_key>"
AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY") or "<your_agentops_key>"

# Initialize Anthropic client and AgentOps session
client = Anthropic(api_key=ANTHROPIC_API_KEY)
agentops.init(AGENTOPS_API_KEY, default_tags=["anthropic-async"])

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


async def generate_message():
    """Generate a Titan message using async context manager for streaming."""
    async with client.messages.create(
        max_tokens=1024,
        model="claude-3-sonnet-20240229",
        messages=[
            {
                "role": "user",
                "content": "You are a Titan; a mech from Titanfall 2. Based on your titan's personality and status, generate a message for your pilot. If Near Destruction, make an all caps death message such as AVENGE ME or UNTIL NEXT TIME.",
            },
            {
                "role": "assistant",
                "content": "Personality: Legion is a relentless and heavy-hitting Titan that embodies brute strength and defensive firepower. He speaks bluntly. Status: Considerable Damage",
            },
            {
                "role": "assistant",
                "content": "Heavy damage detected. Reinforcements would be appreciated, but I can still fight.",
            },
            {
                "role": "user",
                "content": "You are a Titan; a mech from Titanfall 2. Based on your titan's personality and status, generate a message for your pilot. If Near Destruction, make an all caps death message such as AVENGE ME or UNTIL NEXT TIME.",
            },
            {
                "role": "assistant",
                "content": f"Personality: {Personality}. Status: {Health}",
            },
        ],
        stream=True,
    ) as stream:
        message = ""
        async for text in stream.text_stream:
            message += text
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

    # Start both tasks concurrently
    uuids, message = await asyncio.gather(generate_uuids(), generate_message())

    print("\nVerification matrix activated:")
    for u in uuids:
        print(u)

    print("\nTitan Message:", message)


if __name__ == "__main__":
    # Run the main function using asyncio
    asyncio.run(main())
    # End the AgentOps session with success status
    agentops.end_session("Success")

