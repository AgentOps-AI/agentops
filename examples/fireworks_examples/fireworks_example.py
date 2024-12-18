#!/usr/bin/env python
# coding: utf-8

import os
import logging
from fireworks.client import Fireworks
import agentops
from agentops.enums import EndState
from agentops.llms.providers.fireworks import FireworksProvider
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,  # Change to DEBUG to see more detailed output
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
FIREWORKS_API_KEY = os.getenv("FIREWORKS_API_KEY")

if not FIREWORKS_API_KEY:
    raise ValueError("FIREWORKS_API_KEY environment variable is not set")

try:
    # Initialize AgentOps in development mode
    print("Initializing AgentOps in development mode...")
    session = agentops.init(api_key=None)
    print(f"AgentOps initialized. Session URL: {session.session_url}")

    # Initialize Fireworks client
    print("Initializing Fireworks client...")
    client = Fireworks(api_key=FIREWORKS_API_KEY)
    print("Fireworks client initialized.")

    # Initialize and register Fireworks provider
    print("Registering Fireworks provider...")
    provider = FireworksProvider(client)
    provider.set_session(session)  # Set the session before overriding
    provider.override()
    print("Fireworks provider registered.")

    # Set up messages for story generation
    messages = [
        {"role": "system", "content": "You are a creative storyteller."},
        {"role": "user", "content": "Write a short story about a cyber-warrior trapped in the imperial era."}
    ]

    # Test non-streaming completion
    print("Generating story with Fireworks LLM...")
    response = client.chat.completions.create(
        model="accounts/fireworks/models/llama-v3p1-8b-instruct",
        messages=messages
    )
    print("\nLLM Response:")
    print(response.choices[0].message.content)
    print("\nEvent tracking details:")
    print(f"Session URL: {session.session_url}")
    print("Check the AgentOps dashboard to see the tracked LLM event.")

    # Test streaming completion
    print("\nGenerating story with streaming enabled...")
    stream = client.chat.completions.create(
        model="accounts/fireworks/models/llama-v3p1-8b-instruct",
        messages=messages,
        stream=True
    )

    print("\nStreaming LLM Response:")
    for chunk in stream:
        try:
            if hasattr(chunk, 'choices') and chunk.choices and hasattr(chunk.choices[0].delta, 'content'):
                content = chunk.choices[0].delta.content
            else:
                content = chunk
            if content:
                print(content, end="", flush=True)
        except Exception as e:
            logger.error(f"Error processing chunk: {str(e)}")
            continue
    print("\n\nEvent tracking details:")
    print(f"Session URL: {session.session_url}")

    # End session and show detailed stats
    print("\nEnding AgentOps session...")
    try:
        session_stats = session.end_session(
            end_state=EndState.SUCCESS.value,  # Use .value to get the enum value
            end_state_reason="Successfully generated stories using both streaming and non-streaming modes."
        )
        print("\nSession Statistics:")
        if isinstance(session_stats, dict):
            for key, value in session_stats.items():
                print(f"{key}: {value}")
        else:
            print("No session statistics available")
    except Exception as e:
        print(f"Error ending session: {str(e)}")
        print("Session URL for debugging:", session.session_url)

except Exception as e:
    logger.error(f"An error occurred: {str(e)}", exc_info=True)
    if 'session' in locals():
        try:
            session.end_session(
                end_state=EndState.FAIL,
                end_state_reason=f"Error occurred: {str(e)}"
            )
        except Exception as end_error:
            logger.error(f"Error ending session: {str(end_error)}", exc_info=True)
    raise

finally:
    print("\nScript execution completed.")

