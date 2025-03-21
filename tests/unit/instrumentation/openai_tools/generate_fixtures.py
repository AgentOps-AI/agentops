#!/usr/bin/env python
"""
Generate OpenAI Test Fixtures

Quick and dirty script to generate JSON fixtures from real OpenAI API calls.
Dev tool only - no frills, just gets the job done.

Generates fixtures for:
- OpenAI Responses API (standard response and tool calls)
- OpenAI Chat Completions API (standard completion and tool calls)

Usage:
    python -m tests.unit.instrumentation.openai_tools.generate_fixtures
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
FIXTURES_DIR = "../fixtures"  # Relative to this script's location
RESPONSE_FILE = "openai_response.json"
TOOL_CALLS_FILE = "openai_response_tool_calls.json"
CHAT_COMPLETION_FILE = "openai_chat_completion.json"
CHAT_TOOL_CALLS_FILE = "openai_chat_tool_calls.json"

def get_fixtures_dir():
    """Get absolute path to fixtures directory"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), FIXTURES_DIR)

async def main():
    """Blast through API calls and save fixtures"""
    print("Generating fixtures...")
    
    # Create API client
    client = AsyncOpenAI()
    
    # Print fixture directory for debugging
    fixtures_dir = get_fixtures_dir()
    print(f"Using fixtures directory: {fixtures_dir}")
    os.makedirs(fixtures_dir, exist_ok=True)
    
    # PART 1: RESPONSES API FIXTURES
    model = OpenAIResponsesModel(model="gpt-4o", openai_client=client)
    model_settings = ModelSettings(temperature=0.7, top_p=1.0)
    
    # Get standard response
    print("Getting Responses API standard response...")
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
    with open(os.path.join(fixtures_dir, RESPONSE_FILE), "w") as f:
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
    print("Getting Responses API tool calls response...")
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
    with open(os.path.join(fixtures_dir, TOOL_CALLS_FILE), "w") as f:
        json.dump(tool_response.model_dump(), f, indent=2)
    
    # PART 2: CHAT COMPLETIONS API FIXTURES
    
    # Get standard chat completion
    print("Getting Chat Completions API standard response...")
    chat_completion = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is the capital of France?"}
        ],
        temperature=0.7,
        top_p=1.0
    )
    
    # Save standard chat completion
    try:
        chat_completion_dict = chat_completion.model_dump()
    except AttributeError:
        # Fallback if model_dump isn't available
        chat_completion_dict = json.loads(chat_completion.json())
    except Exception as e:
        print(f"Error serializing chat completion: {e}")
        chat_completion_dict = {"error": str(e)}
    
    with open(os.path.join(fixtures_dir, CHAT_COMPLETION_FILE), "w") as f:
        json.dump(chat_completion_dict, f, indent=2)
    
    # Define weather tool for chat completions
    weather_tool_schema = {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather in a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA"
                    },
                    "unit": {
                        "type": "string",
                        "description": "The unit of temperature to use (celsius or fahrenheit)",
                        "enum": ["celsius", "fahrenheit"]
                    }
                },
                "required": ["location", "unit"]
            }
        }
    }
    
    # Get chat completion with tool calls
    print("Getting Chat Completions API tool calls response...")
    chat_tool_calls = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What's the current weather in San Francisco?"}
        ],
        tools=[weather_tool_schema],
        temperature=0.7,
        top_p=1.0
    )
    
    # Save chat completion with tool calls
    try:
        chat_tool_calls_dict = chat_tool_calls.model_dump()
    except AttributeError:
        # Fallback if model_dump isn't available
        chat_tool_calls_dict = json.loads(chat_tool_calls.json())
    except Exception as e:
        print(f"Error serializing chat tool calls: {e}")
        chat_tool_calls_dict = {"error": str(e)}
        
    with open(os.path.join(fixtures_dir, CHAT_TOOL_CALLS_FILE), "w") as f:
        json.dump(chat_tool_calls_dict, f, indent=2)
    
    print(f"✅ Done! Fixtures saved to {fixtures_dir}/")
    print(f"  - {RESPONSE_FILE}")
    print(f"  - {TOOL_CALLS_FILE}")
    print(f"  - {CHAT_COMPLETION_FILE}")
    print(f"  - {CHAT_TOOL_CALLS_FILE}")

if __name__ == "__main__":
    asyncio.run(main())