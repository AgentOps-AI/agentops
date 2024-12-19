#!/usr/bin/env python
# coding: utf-8

"""
Anthropic Sync Example

We are going to create a program called "Nier Storyteller". In short, it uses a message
system similar to Nier Automata's to generate a one sentence summary before creating
a short story.

Example:
{A foolish doll} {died in a world} {of ended dreams.} turns into "In a forgotten land
where sunlight barely touched the ground, a little doll wandered through the remains
of shattered dreams. Its porcelain face, cracked and wea..."
"""

# First, we start by importing Agentops and Anthropic
from anthropic import Anthropic
import agentops
from dotenv import load_dotenv
import os
import random

# Setup environment and API keys
load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY") or "ANTHROPIC KEY HERE"
AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY") or "AGENTOPS KEY HERE"

# Initialize Anthropic client and AgentOps session
client = Anthropic(api_key=ANTHROPIC_API_KEY)
agentops.init(AGENTOPS_API_KEY, default_tags=["anthropic-example"])

"""
As of writing, claude-3-5-sonnet-20240620 has a 150k word, 680k character length with
an 8192 context length. This allows us to set an example for the script.

We have three roles:
- user (the person speaking)
- assistant (the AI itself)
- computer (the way the LLM gets references from)
"""

# Set default story as a script
defaultstory = """In a forgotten land where sunlight barely touched the ground, a little doll wandered through the remains of shattered dreams. Its porcelain face, cracked and weathered, reflected the emptiness that hung in the air like a lingering fog. The doll's painted eyes, now chipped and dull, stared into the distance, searching for something—anything—that still held life. It had once belonged to a child who dreamt of endless adventures, of castles in the clouds and whispered secrets under starry skies. But those dreams had long since crumbled to dust, leaving behind nothing but a hollow world where even hope dared not tread. The doll, a relic of a life that had faded, trudged through the darkness, its tiny feet stumbling over broken wishes and forgotten stories. Each step took more effort than the last, as if the world itself pulled at the doll's limbs, weary and bitter. It reached a place where the ground fell away into an abyss of despair, the edge crumbling under its weight. The doll paused, teetering on the brink. It reached out, as though to catch a fading dream, but there was nothing left to hold onto. With a faint crack, its brittle body gave way, and the doll tumbled silently into the void. And so, in a world where dreams had died, the foolish little doll met its end. There were no tears, no mourning. Only the soft, empty echo of its fall, fading into the darkness, as the land of ended dreams swallowed the last trace of what once was."""

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

# Generate a random sentence
generatedsentence = f"{random.choice(first)} {random.choice(second)} {random.choice(third)}."

# Create a story using the context handler pattern for streaming
print("Generated prompt:", generatedsentence)
print("\nGenerating story...\n")

with client.messages.create(
    max_tokens=2400,
    model="claude-3-sonnet-20240229",
    messages=[
        {
            "role": "user",
            "content": "Create a story based on the three sentence fragments given to you, it has been combined into one below.",
        },
        {
            "role": "assistant",
            "content": "{A foolish doll} {died in a world} {of ended dreams.}",
        },
        {"role": "assistant", "content": defaultstory},
        {
            "role": "user",
            "content": "Create a story based on the three sentence fragments given to you, it has been combined into one below.",
        },
        {"role": "assistant", "content": generatedsentence},
    ],
    stream=True,
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)

print("\n\nStory generation complete!")

# End the AgentOps session with success status
agentops.end_session("Success")
