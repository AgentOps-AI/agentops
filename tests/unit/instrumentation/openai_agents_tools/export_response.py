"""
Export OpenAI Responses API Data

This script creates a simple agent using the OpenAI Responses API and exports the response
data to a JSON file. This exported data can be used to create test fixtures for the
AgentOps instrumentation tests.

Usage:
    python -m tests.unit.instrumentation.openai_agents_tools.export_response

The output will be written to a file named `openai_response_export.json` in the 
current directory.
"""

import asyncio
import json
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai.types.responses import Response
from agents import Agent
from agents.model_settings import ModelSettings
from agents.models.openai_responses import OpenAIResponsesModel

# Load environment variables from .env file
load_dotenv()

async def export_response_data():
    """
    Create a simple agent, send a request to the OpenAI Responses API, and export the
    response data to a JSON file.
    """
    print("Creating OpenAI client...")
    openai_client = AsyncOpenAI()

    print("Creating model...")
    model = OpenAIResponsesModel(
        model="gpt-4o",
        openai_client=openai_client
    )

    print("Sending request to OpenAI Responses API...")
    model_settings = ModelSettings(
        temperature=0.7,
        top_p=1.0,
    )
    
    # Simple request to ask a factual question
    response = await model._fetch_response(
        system_instructions="You are a helpful assistant.",
        input="What is the capital of France?",
        model_settings=model_settings,
        tools=[],
        output_schema=None,
        handoffs=[],
        stream=False
    )

    print("Response received!")
    
    # Convert response to a serializable format
    response_dict = response.model_dump()
    
    # Write to fixtures directory
    fixtures_dir = "../fixtures"
    os.makedirs(fixtures_dir, exist_ok=True)
    
    output_file = os.path.join(fixtures_dir, "openai_response.json")
    with open(output_file, "w") as f:
        json.dump(response_dict, f, indent=2)
    
    print(f"Response data written to {output_file}")
    
    # Also print useful parts of the response
    print("\nResponse Highlights:")
    print(f"ID: {response.id}")
    print(f"Model: {response.model}")
    print(f"Status: {response.status}")
    
    print("\nOutput Items:")
    for i, item in enumerate(response.output):
        print(f"Item {i+1} type: {item.type}")
        if item.type == "message":
            print(f"  Role: {item.role}")
            for j, content in enumerate(item.content):
                print(f"  Content {j+1} type: {content.type}")
                if content.type == "output_text":
                    print(f"    Text: {content.text}")
    
    if response.usage:
        print("\nToken Usage:")
        print(f"  Input tokens: {response.usage.input_tokens}")
        print(f"  Output tokens: {response.usage.output_tokens}")
        print(f"  Total tokens: {response.usage.total_tokens}")
        if hasattr(response.usage, "output_tokens_details") and response.usage.output_tokens_details:
            print(f"  Reasoning tokens: {response.usage.output_tokens_details.reasoning_tokens}")
    
    return response

# Create a function to run with tool calls to get that format too
async def export_tool_calls_response():
    """
    Create a request that will trigger tool calls and export the response.
    """
    print("\n\nCreating OpenAI client for tool calls request...")
    openai_client = AsyncOpenAI()

    print("Creating model...")
    model = OpenAIResponsesModel(
        model="gpt-4o",
        openai_client=openai_client
    )

    from agents import function_tool
    
    # Define a simple tool for getting weather information - without default parameters
    def get_weather(location: str, unit: str) -> str:
        """Get the current weather in a location.
        
        Args:
            location: The city and state, e.g. San Francisco, CA
            unit: The unit of temperature to use (celsius or fahrenheit)
            
        Returns:
            A string with the current weather information
        """
        return f"The weather in {location} is 22 degrees {unit}."
    
    weather_tool = function_tool(
        get_weather,
        name_override="get_weather",
        description_override="Get the current weather in a location"
    )

    print("Sending request to OpenAI Responses API with tool...")
    model_settings = ModelSettings(
        temperature=0.7,
        top_p=1.0,
    )
    
    # Request that should trigger a tool call
    response = await model._fetch_response(
        system_instructions="You are a helpful assistant.",
        input="What's the current weather in San Francisco?",
        model_settings=model_settings,
        tools=[weather_tool],
        output_schema=None,
        handoffs=[],
        stream=False
    )

    print("Tool call response received!")
    
    # Convert response to a serializable format
    response_dict = response.model_dump()
    
    # Write to fixtures directory
    fixtures_dir = "../fixtures"
    os.makedirs(fixtures_dir, exist_ok=True)
    
    output_file = os.path.join(fixtures_dir, "openai_response_tool_calls.json")
    with open(output_file, "w") as f:
        json.dump(response_dict, f, indent=2)
    
    print(f"Tool call response data written to {output_file}")
    
    # Also print useful parts of the response
    print("\nTool Call Response Highlights:")
    print(f"ID: {response.id}")
    print(f"Model: {response.model}")
    print(f"Status: {response.status}")
    
    print("\nOutput Items:")
    for i, item in enumerate(response.output):
        print(f"Item {i+1} type: {item.type}")
        if item.type == "function_tool_call":
            print(f"  Call ID: {item.call_id}")
            print(f"  Function: {item.function}")
            print(f"  Status: {item.status}")
            print(f"  Arguments: {item.arguments}")
    
    if response.usage:
        print("\nToken Usage:")
        print(f"  Input tokens: {response.usage.input_tokens}")
        print(f"  Output tokens: {response.usage.output_tokens}")
        print(f"  Total tokens: {response.usage.total_tokens}")
    
    return response

def main():
    """Main function to run both export functions."""
    asyncio.run(export_response_data())
    asyncio.run(export_tool_calls_response())

if __name__ == "__main__":
    main()