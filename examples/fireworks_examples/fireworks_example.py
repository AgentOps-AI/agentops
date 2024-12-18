#!/usr/bin/env python
# coding: utf-8

import os
import logging
import asyncio
from fireworks.client import Fireworks
import agentops
from agentops.enums import EndState
from agentops.llms.providers.fireworks import FireworksProvider
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG to see formatted prompt
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
FIREWORKS_API_KEY = os.getenv("FIREWORKS_API_KEY")

if not FIREWORKS_API_KEY:
    raise ValueError("FIREWORKS_API_KEY environment variable is not set")

try:
    # Initialize AgentOps client and start session
    print("Initializing AgentOps client...")
    ao_client = agentops.Client()
    ao_client.initialize()  # Initialize before starting session
    session = ao_client.start_session()

    if not session:
        raise RuntimeError("Failed to create AgentOps session")

    print(f"AgentOps initialized. Session URL: {session.session_url}")
    print("Session ID:", session.session_id)
    print("Session tracking enabled:", bool(session))

    # Initialize Fireworks client
    print("Initializing Fireworks client...")
    client = Fireworks(api_key=FIREWORKS_API_KEY)
    print("Fireworks client initialized.")

    # Initialize and register Fireworks provider
    print("Registering Fireworks provider...")
    provider = FireworksProvider(client)
    provider.set_session(session)
    provider.override()
    print("Fireworks provider registered.")

    # Set up messages for story generation
    messages = [
        {"role": "system", "content": "You are a creative storyteller."},
        {"role": "user", "content": "Write a short story about a cyber-warrior trapped in the imperial era."},
    ]

    # 1. Test synchronous non-streaming completion
    print("\n1. Generating story with synchronous non-streaming completion...")
    response = client.chat.completions.create(
        model="accounts/fireworks/models/llama-v3p1-8b-instruct", messages=messages
    )
    print("\nSync Non-streaming Response:")
    print(response.choices[0].message.content)
    print("\nEvent recorded for sync non-streaming completion")

    # 2. Test asynchronous non-streaming completion
    print("\n2. Generating story with asynchronous non-streaming completion...")
    async def async_completion():
        response = await client.chat.completions.acreate(
            model="accounts/fireworks/models/llama-v3p1-8b-instruct", messages=messages
        )
        print("\nAsync Non-streaming Response:")
        print(response.choices[0].message.content)
        print("\nEvent recorded for async non-streaming completion")

    asyncio.run(async_completion())

    # 3. Test synchronous streaming completion
    print("\n3. Generating story with synchronous streaming...")
    stream = client.chat.completions.create(
        model="accounts/fireworks/models/llama-v3p1-8b-instruct", messages=messages, stream=True
    )

    print("\nSync Streaming Response:")
    try:
        if asyncio.iscoroutine(stream):
            stream = asyncio.run(stream)
        for chunk in stream:
            if hasattr(chunk, "choices") and chunk.choices and hasattr(chunk.choices[0].delta, "content"):
                content = chunk.choices[0].delta.content
                if content:
                    print(content, end="", flush=True)
    except Exception as e:
        logger.error(f"Error processing streaming response: {str(e)}")
    print()  # New line after streaming

    # 4. Test asynchronous streaming completion
    print("\n4. Generating story with asynchronous streaming...")
    async def async_streaming():
        try:
            stream = await client.chat.completions.acreate(
                model="accounts/fireworks/models/llama-v3p1-8b-instruct", messages=messages, stream=True
            )
            print("\nAsync Streaming Response:")
            async for chunk in stream:
                if hasattr(chunk, "choices") and chunk.choices and hasattr(chunk.choices[0].delta, "content"):
                    content = chunk.choices[0].delta.content
                    if content:
                        print(content, end="", flush=True)
        except Exception as e:
            logger.error(f"Error in async streaming: {str(e)}")
        print()  # New line after streaming

    asyncio.run(async_streaming())

    # End session and show detailed stats
    print("\nEnding AgentOps session...")
    try:
        print("\nSession Statistics:")
        print(f"Session ID before end: {session.session_id}")  # Debug logging
        session_stats = session.end_session(end_state=EndState.SUCCESS)
        print(f"Session ID after end: {session.session_id}")  # Debug logging
        if isinstance(session_stats, dict):
            print(f"Duration: {session_stats.get('duration', 'N/A')}")
            print(f"Cost: ${float(session_stats.get('cost', 0.00)):.2f}")
            print(f"LLM Events: {session_stats.get('llm_events', 0)}")
            print(f"Tool Events: {session_stats.get('tool_events', 0)}")
            print(f"Action Events: {session_stats.get('action_events', 0)}")
            print(f"Error Events: {session_stats.get('error_events', 0)}")
            print(f"Session URL: {session.session_url}")  # Add session URL to output
        else:
            print("No session statistics available")
            print("Session URL for debugging:", session.session_url)
    except Exception as e:
        print(f"Error ending session: {str(e)}")
        print("Session URL for debugging:", session.session_url)

except Exception as e:
    logger.error(f"An error occurred: {str(e)}", exc_info=True)
    if "session" in locals():
        try:
            session.end_session(end_state=EndState.FAIL, end_state_reason=f"Error occurred: {str(e)}")
        except Exception as end_error:
            logger.error(f"Error ending session: {str(end_error)}", exc_info=True)
    raise

finally:
    print("\nScript execution completed.")

