#!/usr/bin/env python
# coding: utf-8

# # Voyage AI Integration Example with AgentOps
#
# This notebook demonstrates how to use the Voyage AI provider with AgentOps for embedding operations using a mock client for demonstration purposes.

import os
import json
import asyncio
from voyageai import Client as VoyageClient
from agentops import Client as AgentopsClient
from agentops.llms.providers.voyage import VoyageProvider
from agentops.event import LLMEvent
from agentops.helpers import check_call_stack_for_agent_id


class MockVoyageClient:
    def embed(self, texts, **kwargs):
        """Mock embed method that returns minimal response."""
        return {
            "model": "default",
            "usage": {"prompt_tokens": 10},
            "data": [{"embedding": [0.0] * 1024}],
        }

    async def aembed(self, texts, **kwargs):
        """Mock async embed method."""
        return self.embed(texts, **kwargs)


class MockSession:
    """Mock session for offline testing."""

    def __init__(self):
        self.events = []
        self.session_url = "https://app.agentops.ai/sessions/mock"

    def record(self, event):
        """Record event with minimal data exposure."""
        try:
            event_data = {
                "type": "llms",
                "model": "default",
                "input_tokens": 10,
                "output_tokens": 0,
                "input": getattr(event, "input", ""),
                "output": {
                    "type": "embedding",
                    "data": ["<vector data redacted>"],
                },
                "metadata": {"text": getattr(event, "input", "")},
            }
            print("\nEvent data (redacted):")
            print(json.dumps(event_data, indent=2))
            self.events.append(event)
        except Exception as e:
            print("Warning: Event recording failed")


def main():
    """Run the example with proper error handling."""
    # Initialize clients with proper API key checks
    ao_client = None
    voyage_client = None
    session = None

    # Check for AgentOps API key
    if "AGENTOPS_API_KEY" not in os.environ:
        print("\nWarning: AGENTOPS_API_KEY not found in environment variables")
        print("To use AgentOps tracking, set your API key:")
        print("    export AGENTOPS_API_KEY='your-key-here'")
        print("Continuing with mock session for demonstration")
        session = MockSession()
    else:
        try:
            ao_client = AgentopsClient()
            session = ao_client.start_session()
            print("\nStarted AgentOps session successfully")
        except Exception as e:
            print(f"\nWarning: Failed to start AgentOps session: {e}")
            print("Continuing with mock session for demonstration")
            session = MockSession()

    # Check for Voyage AI API key
    if "VOYAGE_API_KEY" not in os.environ:
        print("\nWarning: VOYAGE_API_KEY not found in environment variables")
        print("To use Voyage AI embeddings, set your API key:")
        print("    export VOYAGE_API_KEY='your-key-here'")
        print("Continuing with mock client for demonstration")
        voyage_client = MockVoyageClient()
    else:
        try:
            voyage_client = VoyageClient()
            print("\nInitialized Voyage AI client successfully")
        except Exception as e:
            print(f"\nWarning: Failed to initialize Voyage AI client: {e}")
            print("Continuing with mock client for demonstration")
            voyage_client = MockVoyageClient()

    # Initialize provider with appropriate client
    provider = VoyageProvider(client=voyage_client)
    provider.override()

    try:
        # Create embeddings with session tracking
        test_input = "Hello, Voyage!"
        result = provider.embed(test_input, session=session)

        # Print event data for verification (with sensitive data redacted)
        print("\nEvent data (redacted):")
        event_data = {
            "type": "llms",
            "model": result.get("model", "voyage-01"),
            "prompt_tokens": result.get("usage", {}).get("input_tokens", 0),
            "completion_tokens": 0,
            "prompt": test_input,
            "completion": {"type": "embedding", "vector": ["<vector data redacted for brevity>"]},
            "params": {"input_text": test_input},
            "returns": {
                "usage": result.get("usage", {}),
                "model": result.get("model", "voyage-01"),
            },
        }
        print(json.dumps(event_data, indent=2))

        # Print basic stats
        print(f"\nEmbedding dimension: {len(result['data'][0]['embedding'])}")
        print(f"Token usage: {result['usage']}")

        # Display session URL
        if isinstance(session, MockSession):
            print(f"\nMock Session URL: {session.session_url}")
        elif hasattr(session, "session_url"):
            print(f"\nAgentOps Session URL: {session.session_url}")
        else:
            print("\nWarning: No session URL available")

    finally:
        # Clean up provider override and end session
        provider.undo_override()
        if isinstance(session, MockSession):
            print("\nMock session completed successfully!")
        elif session is not None and ao_client is not None:
            try:
                ao_client.end_session("Success", "Example completed successfully")
                print("\nSession completed successfully!")
                if hasattr(session, "session_url"):
                    print(f"View session at: {session.session_url}")
            except Exception as e:
                print(f"\nWarning: Failed to end AgentOps session: {e}")


if __name__ == "__main__":
    main()
