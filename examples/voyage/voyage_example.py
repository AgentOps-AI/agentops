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


class MockVoyageClient:
    def embed(self, texts, **kwargs):
        return {
            "data": [{"embedding": [0.1] * 1024, "index": 0, "object": "embedding"}],
            "model": "voyage-01",
            "object": "list",
            "usage": {"prompt_tokens": 10, "completion_tokens": 0},
        }

    async def aembed(self, texts, **kwargs):
        return self.embed(texts, **kwargs)


def main():
    # Set AgentOps API key
    os.environ["AGENTOPS_API_KEY"] = "8b95388c-ee56-499d-a940-c1d6a2ba7f0c"

    # Initialize clients
    voyage_client = MockVoyageClient()
    ao_client = AgentopsClient()

    # Initialize session
    session = ao_client.initialize()
    print(f"Session URL: {session.session_url}")

    # Set up Voyage provider with mock client
    provider = VoyageProvider(client=voyage_client)
    provider.override()

    try:
        # Create embeddings with session tracking
        text = "Hello, Voyage!"
        result = provider.embed(text, session=session)
        print(f"\nEmbedding dimension: {len(result['data'][0]['embedding'])}")

        # Print event data for verification
        events = session.get_events()
        if events:
            latest_event = events[-1]
            print("\nLatest Event Data:")
            print(json.dumps(latest_event, indent=2))
    finally:
        # Clean up provider override
        provider.undo_override()
        # End session
        ao_client.end_session("Success", "Example completed successfully")
        print(f"\nSession ended. View session at: {session.session_url}")


if __name__ == "__main__":
    main()
