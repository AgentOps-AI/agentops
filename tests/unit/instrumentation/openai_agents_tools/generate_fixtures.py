#!/usr/bin/env python
"""
Generate OpenAI Agents SDK Test Fixtures

Quick and dirty script to generate JSON fixtures from real OpenAI API calls.
Dev tool only - no frills, just gets the job done.

Usage:
    python -m tests.unit.instrumentation.openai_agents_tools.generate_fixtures
"""

import asyncio
import json
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import function_tool
from agents.model_settings import ModelSettings
from agents.models.openai_responses import OpenAIResponsesModel

# Load environment variables from .env file
load_dotenv()

# Output paths
FIXTURES_DIR = "../fixtures"
RESPONSE_FILE = "openai_response.json"
TOOL_CALLS_FILE = "openai_response_tool_calls.json"

async def main():
    """Blast through API calls and save fixtures"""
    print("Generating fixtures...")
    os.makedirs(FIXTURES_DIR, exist_ok=True)
    
    # Create API client
    client = AsyncOpenAI()
    model = OpenAIResponsesModel(model="gpt-4o", openai_client=client)
    model_settings = ModelSettings(temperature=0.7, top_p=1.0)
    
    # Get standard response
    print("Getting standard response...")
    response = await model._fetch_response(
        system_instructions="You are a helpful assistant.",
        input="What is the capital of France?",
        model_settings=model_settings,
        tools=[],
        output_schema=None,
        handoffs=[],
        stream=False
    )
    
    # Save standard response
    with open(os.path.join(FIXTURES_DIR, RESPONSE_FILE), "w") as f:
        json.dump(response.model_dump(), f, indent=2)
    
    # Define tool
    def get_weather(location: str, unit: str) -> str:
        return f"The weather in {location} is 22 degrees {unit}."
    
    weather_tool = function_tool(
        get_weather,
        name_override="get_weather",
        description_override="Get the current weather in a location"
    )
    
    # Get tool calls response
    print("Getting tool calls response...")
    tool_response = await model._fetch_response(
        system_instructions="You are a helpful assistant.",
        input="What's the current weather in San Francisco?",
        model_settings=model_settings,
        tools=[weather_tool],
        output_schema=None,
        handoffs=[],
        stream=False
    )
    
    # Save tool calls response
    with open(os.path.join(FIXTURES_DIR, TOOL_CALLS_FILE), "w") as f:
        json.dump(tool_response.model_dump(), f, indent=2)
    
    print(f"✅ Done! Fixtures saved to {FIXTURES_DIR}/")
    print(f"  - {RESPONSE_FILE}")
    print(f"  - {TOOL_CALLS_FILE}")

if __name__ == "__main__":
    asyncio.run(main())