#!/usr/bin/env python
# coding: utf-8

"""
Anthropic Sync Example - Story Generator
This example demonstrates sync streaming with the Anthropic API using AgentOps.
"""

import os
import random
import anthropic
from dotenv import load_dotenv
from agentops import Client
from agentops.llms.providers.anthropic import AnthropicProvider
from agentops.session import EndState

# Load environment variables
load_dotenv()

# Define sentence fragment lists for story generation
first = [
    "A unremarkable soldier",
    "A lone swordsman",
    "A lone lancer",
    "A lone pugilist",
    "A dual-wielder",
    "A weaponless soldier",
    "A beautiful android",
    "A small android",
    "A double-crossing android",
    "A weapon carrying android",
]

second = [
    "felt despair at this cold world",
    "held nothing back",
    "gave it all",
    "could not get up again",
    "grimaced in anger",
    "missed the chance of a lifetime",
    "couldn't find a weakpoint",
    "was overwhelmed",
    "was totally outmatched",
    "was distracted by a flower",
    "hesitated to land the killing blow",
    "was attacked from behind",
    "fell to the ground",
]

third = [
    "in a dark hole beneath a city",
    "underground",
    "at the enemy's lair",
    "inside an empty ship",
    "at a tower built by the gods",
    "on a tower smiled upon by angels",
    "inside a tall tower",
    "at a peace-loving village",
    "at a village of refugees",
    "in the free skies",
    "below dark skies",
    "in a blood-soaked battlefield",
]

def generate_story():
    """Generate a story using the Anthropic API with streaming."""
    # Initialize AgentOps client
    ao_client = Client()
    ao_client.initialize()
    session = ao_client.start_session()

    try:
        # Initialize Anthropic client and provider
        anthropic_client = anthropic.Client(api_key=os.getenv("ANTHROPIC_API_KEY"))
        provider = AnthropicProvider(client=anthropic_client, session=session)

        # Generate a random prompt
        prompt = f"A {random.choice(first)} {random.choice(second)} {random.choice(third)}."
        print(f"Generated prompt: {prompt}\n")
        print("Generating story...\n")

        # Create message with provider's streaming
        with provider.create_stream(
            max_tokens=2048,
            model="claude-3-sonnet-20240229",
            messages=[
                {
                    "role": "user",
                    "content": "Create a story based on the following prompt. Make it dark and atmospheric, similar to NieR:Automata's style.",
                },
                {"role": "assistant", "content": prompt},
            ],
            stream=True
        ) as stream:
            for text in stream.text_stream:
                print(text, end="", flush=True)
            print("\nStory generation complete!")

        # End session with success status
        session.end_session(end_state=EndState.SUCCESS)
    except Exception as e:
        print(f"Error generating story: {e}")
        session.end_session(end_state=EndState.ERROR)

if __name__ == "__main__":
    generate_story()

