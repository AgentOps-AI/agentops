#!/usr/bin/env python
# coding: utf-8

# # Monitoring Mistral with AgentOps
#
# This notebook demonstrates how to monitor and analyze Mistral model runs using AgentOps. We'll cover:
# - Basic model completions with monitoring
# - Streaming responses
# - Async operations
# - Custom event tracking

# ## Setup
#
# First, let's install the required packages:

import asyncio
import os
from mistralai import Mistral
import agentops
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# Function to validate API keys
def validate_api_keys():
    mistral_key = os.getenv("MISTRAL_API_KEY")
    agentops_key = os.getenv("AGENTOPS_API_KEY")

    if not mistral_key or not agentops_key:
        print("Warning: Missing API keys. Please set MISTRAL_API_KEY and AGENTOPS_API_KEY in your .env file")
        print("Using placeholder responses for demonstration purposes.")
        return False
    return True


# Initialize clients with validation
has_valid_keys = validate_api_keys()

try:
    if has_valid_keys:
        # Create a new session for monitoring Mistral interactions
        agentops.init(os.getenv("AGENTOPS_API_KEY"), session_name="mistral-monitoring")
        client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
        print("Successfully initialized AgentOps and Mistral clients")
    else:
        print("Running in demonstration mode with placeholder responses")
except Exception as e:
    print(f"Error initializing clients: {str(e)}")
    has_valid_keys = False


# ## Basic Completion with Monitoring
#
# Let's create a simple function that gets completions from Mistral and is monitored by AgentOps:


@agentops.track_agent(name="mistral-agent")
def get_completion(prompt):
    """Get a completion from Mistral with monitoring."""
    if not has_valid_keys:
        return "This is a placeholder response. Please set valid API keys to get actual completions."

    try:
        response = client.chat.complete(model="mistral-small-latest", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error getting completion: {str(e)}")
        return f"Error: {str(e)}"


# Example usage with session management
agentops.init(os.getenv("AGENTOPS_API_KEY"), session_name="mistral-basic")
response = get_completion("Explain quantum computing in simple terms")
print(response)
agentops.end_session("Basic completion completed")


# ## Streaming Responses
#
# For longer responses, you might want to use streaming to get tokens as they're generated:


@agentops.track_agent(name="mistral-stream-agent")
def get_streaming_completion(prompt):
    """Get a streaming completion from Mistral with monitoring."""
    if not has_valid_keys:
        print("This is a placeholder streaming response. Please set valid API keys.")
        return "Placeholder streaming response"

    try:
        response = client.chat.stream(model="mistral-small-latest", messages=[{"role": "user", "content": prompt}])

        result = ""
        for chunk in response:
            if chunk.data.choices[0].finish_reason == "stop":
                return result
            result += chunk.data.choices[0].delta.content
            print(chunk.data.choices[0].delta.content, end="")
        return result
    except Exception as e:
        print(f"Error in streaming: {str(e)}")
        return f"Error: {str(e)}"


# Example usage with session management
agentops.init(os.getenv("AGENTOPS_API_KEY"), session_name="mistral-stream")
response = get_streaming_completion("What is machine learning?")
agentops.end_session("Streaming completion completed")


# ## Async Operations
#
# For better performance in async applications:


@agentops.track_agent(name="mistral-async-agent")
async def get_async_completion(prompt):
    """Get an async completion from Mistral with monitoring."""
    if not has_valid_keys:
        return "This is a placeholder async response. Please set valid API keys."

    try:
        response = await client.chat.complete_async(
            model="mistral-small-latest", messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error in async completion: {str(e)}")
        return f"Error: {str(e)}"


# Example usage with session management
async def main():
    agentops.init(os.getenv("AGENTOPS_API_KEY"), session_name="mistral-async")
    response = await get_async_completion("What are the benefits of async programming?")
    print(response)
    agentops.end_session("Async completion completed")


if __name__ == "__main__":
    asyncio.run(main())
else:
    # For notebook execution, create a new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())


# ## Custom Event Tracking
#
# Track specific functions in your application:


@agentops.record_action("process-response")
def process_response(response):
    """Process and analyze the model's response."""
    try:
        # Add your processing logic here
        word_count = len(response.split())
        print(f"Processing response with {word_count} words")
        return word_count
    except Exception as e:
        print(f"Error processing response: {str(e)}")
        return 0


# Example usage with session management
agentops.init(os.getenv("AGENTOPS_API_KEY"), session_name="mistral-processing")
response = get_completion("Explain the theory of relativity")
word_count = process_response(response)
print(f"Response word count: {word_count}")
agentops.end_session("Processing completed")


# ## Multiple Prompts
#
# Track multiple interactions in a single session:

# Start a new session for multiple prompts
agentops.init(os.getenv("AGENTOPS_API_KEY"), session_name="mistral-multi")
prompts = ["What is artificial intelligence?", "How does natural language processing work?", "Explain neural networks"]

responses = []
for prompt in prompts:
    response = get_completion(prompt)
    responses.append(response)
    print(f"\nPrompt: {prompt}\nResponse: {response}\n")

# End the final session
agentops.end_session("Multiple prompts completed")
