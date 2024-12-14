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
    # Initialize clients with mock session for offline testing
    class MockSession:
        def __init__(self):
            self.events = []
            self.session_url = "mock-session-url"

        def record(self, event):
            self.events.append(event)

        def get_events(self):
            return self.events

    voyage_client = MockVoyageClient()  # Use mock client for testing
    ao_client = AgentopsClient()
    session = MockSession()  # Use mock session for offline testing

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
            event_data = {
                "type": latest_event.event_type,
                "model": latest_event.model,
                "prompt_tokens": latest_event.prompt_tokens,
                "completion_tokens": latest_event.completion_tokens,
                "prompt": latest_event.prompt,  # Should be the input text
                "completion": {
                    "type": "embedding",
                    "vector": latest_event.completion[:5] + ["..."],  # Show first 5 dimensions
                },
                "params": latest_event.params,  # Should contain kwargs
                "returns": {
                    "usage": latest_event.returns.get("usage", {}),
                    "model": latest_event.returns.get("model", ""),
                    "data": "[embedding data truncated]",
                },
            }
            print("\nLatest Event Data:")
            print(json.dumps(event_data, indent=2))
    finally:
        # Clean up provider override
        provider.undo_override()
        print("\nExample completed successfully")


if __name__ == "__main__":
    main()
