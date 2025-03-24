# To run this file from project root: AGENTOPS_LOG_LEVEL=debug uv run examples/openai_responses/dual_api_example.py
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables for API keys
load_dotenv()

# Import OpenAI for both API types
import openai
from openai import OpenAI
from agents import Agent, Runner

# Import AgentOps
import agentops

async def chat_completions_request(client, prompt):
    """Make a request using the OpenAI Chat Completions API."""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    
    return response.choices[0].message.content

async def responses_request(client, prompt):
    """Make a request using the OpenAI Agents SDK (Response API format)."""
    response = client.responses.create(
        model="gpt-4o",
        input=prompt,
    )
    return response

async def main():
    """Run both API formats to demonstrate response instrumentation."""
    # Initialize AgentOps with instrumentation enabled
    agentops.init()
    
    # Set up the OpenAI client
    client = OpenAI()
    
    # Make a Chat Completions API request
    chat_result = await chat_completions_request(
        client, 
        "Explain the concept of async/await in Python in one sentence."
    )
    print(f"Chat Completions Result: {chat_result}")
    
    # Make an Responses API request
    responses_result = await responses_request(
        client,
        "Explain the concept of recursion in one sentence."
    )
    print(f"Responses Result: {responses_result}")

if __name__ == "__main__":
    asyncio.run(main())