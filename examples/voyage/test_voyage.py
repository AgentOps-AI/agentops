import os
import agentops
from agentops.llms.providers.voyage import VoyageProvider


# Set up mock client
class MockVoyageClient:
    def embed(self, texts, **kwargs):
        return {"embeddings": [[0.1] * 1024], "model": "voyage-01", "usage": {"prompt_tokens": 10}}


# Initialize AgentOps client
ao_client = agentops.Client()

# Configure client with valid UUID format API key
ao_client.configure(
    api_key="00000000-0000-0000-0000-000000000000",
    endpoint="https://api.agentops.ai",
    instrument_llm_calls=True,  # Enable LLM call tracking
    auto_start_session=False,  # We'll manage the session manually
)

# Initialize the client
ao_client.initialize()

# Create provider with mock client
provider = VoyageProvider(MockVoyageClient())

# Start a session
session = ao_client.start_session()

if session:
    # Run test embedding with session
    text = "The quick brown fox jumps over the lazy dog."
    result = provider.embed(text, session=session)

    print(f"Embedding dimension: {len(result['embeddings'][0])}")
    print(f"Token usage: {result['usage']}")
    print(f"\nAgentOps Session Link: {session.session_url}")

    # End the session
    ao_client.end_session("Success", "Test completed successfully")
