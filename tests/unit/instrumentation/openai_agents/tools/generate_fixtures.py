#!/usr/bin/env python
"""
Generate OpenAI Agents Test Fixtures

Quick and dirty script to generate JSON fixtures from real OpenAI Agents API calls.
Dev tool only - no frills, just gets the job done.

Generates fixtures for:
- OpenAI Agents API (standard response)
- OpenAI Agents API with tool usage

Usage:
    python -m tests.unit.instrumentation.openai_agents_tools.generate_fixtures
"""

import asyncio
import json
import os
from dotenv import load_dotenv
from typing import Any, Dict

# Load environment variables from .env file
load_dotenv()

# Output paths
FIXTURES_DIR = "../fixtures"  # Relative to this script's location
AGENT_RESPONSE_FILE = "openai_agents_response.json"
AGENT_TOOL_RESPONSE_FILE = "openai_agents_tool_response.json"


def get_fixtures_dir():
    """Get absolute path to fixtures directory"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), FIXTURES_DIR)


def model_to_dict(obj: Any) -> Dict:
    """Convert an object to a dictionary, handling nested objects."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [model_to_dict(item) for item in obj]
    if isinstance(obj, dict):
        return {key: model_to_dict(value) for key, value in obj.items()}

    # For other objects, get their attributes
    result = {}
    for key in dir(obj):
        if not key.startswith("_") and not callable(getattr(obj, key)):
            try:
                value = getattr(obj, key)
                result[key] = model_to_dict(value)
            except Exception as e:
                result[key] = f"<Error: {e}>"
    return result


async def generate_standard_agent_response():
    """Generate a standard response fixture from OpenAI Agents API."""
    print("Getting Agents API standard response...")

    try:
        from agents import Agent, Runner

        agent = Agent(
            name="Fixture Generation Agent",
            instructions="You are a helpful assistant designed to generate test fixtures. Respond concisely.",
        )

        result = await Runner.run(agent, "What is the capital of France?")

        # Convert to dict and save to file
        result_dict = model_to_dict(result)
        fixtures_dir = get_fixtures_dir()
        os.makedirs(fixtures_dir, exist_ok=True)

        output_path = os.path.join(fixtures_dir, AGENT_RESPONSE_FILE)
        with open(output_path, "w") as f:
            json.dump(result_dict, f, indent=2, default=str)

        print(f"✅ Saved standard agent response to {output_path}")
        return result_dict

    except Exception as e:
        print(f"❌ Error generating standard agent response: {e}")
        return {"error": str(e)}


async def generate_tool_agent_response():
    """Generate a tool-using response fixture from OpenAI Agents API."""
    print("Getting Agents API tool calls response...")

    try:
        from agents import Agent, Runner, function_tool

        # Define a simple tool
        def get_weather(location: str, unit: str = "celsius") -> str:
            """Get weather information for a location."""
            return f"The weather in {location} is 22 degrees {unit}."

        weather_tool = function_tool(
            get_weather, name_override="get_weather", description_override="Get the current weather in a location"
        )

        agent = Agent(
            name="Tool Fixture Generation Agent",
            instructions="You are a helpful assistant designed to generate test fixtures. Use tools when appropriate.",
            tools=[weather_tool],
        )

        result = await Runner.run(agent, "What's the weather in Paris?")

        # Convert to dict and save to file
        result_dict = model_to_dict(result)
        fixtures_dir = get_fixtures_dir()
        os.makedirs(fixtures_dir, exist_ok=True)

        output_path = os.path.join(fixtures_dir, AGENT_TOOL_RESPONSE_FILE)
        with open(output_path, "w") as f:
            json.dump(result_dict, f, indent=2, default=str)

        print(f"✅ Saved tool agent response to {output_path}")
        return result_dict

    except Exception as e:
        print(f"❌ Error generating tool agent response: {e}")
        return {"error": str(e)}


async def main():
    """Blast through API calls and save fixtures"""
    print("Generating fixtures...")

    # Print fixture directory for debugging
    fixtures_dir = get_fixtures_dir()
    print(f"Using fixtures directory: {fixtures_dir}")
    os.makedirs(fixtures_dir, exist_ok=True)

    # Generate all fixtures
    await generate_standard_agent_response()
    await generate_tool_agent_response()

    print(f"\n✅ Done! Fixtures saved to {fixtures_dir}/")
    print(f"  - {AGENT_RESPONSE_FILE}")
    print(f"  - {AGENT_TOOL_RESPONSE_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
