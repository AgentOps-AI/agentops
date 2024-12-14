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
    # Initialize clients
    ao_client = AgentopsClient()
    session = None

    try:
        session = ao_client.start_session()
        print("Started AgentOps session")
    except Exception as e:
        print(f"Warning: Failed to start AgentOps session: {e}")
        print("Continuing with mock session for demonstration")
        session = MockSession()

    # Check for API keys
    if "AGENTOPS_API_KEY" not in os.environ:
        print("Note: AGENTOPS_API_KEY not set. Using mock session for demonstration.")
        if not isinstance(session, MockSession):
            session = MockSession()
    if "VOYAGE_API_KEY" not in os.environ:
        print("Note: VOYAGE_API_KEY not set. Using mock client for demonstration.")

    voyage_client = MockVoyageClient()  # Use mock client for testing
    provider = VoyageProvider(client=voyage_client)
    provider.override()

    try:
        # Create embeddings with session tracking
        test_input = "Hello, Voyage!"
        result = provider.embed(test_input, session=session)

        # Print event data for verification
        print("\nEvent data:")
        event_data = {
            "type": "llms",
            "model": "default",
            "prompt_tokens": 10,
            "completion_tokens": 0,
            "prompt": test_input,
            "completion": {"type": "embedding", "vector": result["data"][0]["embedding"][:5] + ["..."]},
            "params": {"input_text": test_input},
            "returns": {
                "usage": result["usage"],
                "model": "default",
                "data": [{"embedding": result["data"][0]["embedding"]}],
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
            print("\nSession completed successfully!")
            print(f"View session at: {session.session_url}")
        elif session is not None:
            try:
                ao_client.end_session("Success", "Example completed successfully")
                print("\nSession completed successfully!")
                if hasattr(session, "session_url"):
                    print(f"View session at: {session.session_url}")
            except Exception as e:
                print(f"\nWarning: Failed to end AgentOps session: {e}")


if __name__ == "__main__":
    main()
