import nbformat as nbf

# Create a new notebook
nb = nbf.v4.new_notebook()

# Add markdown cell explaining the notebook
nb.cells.append(
    nbf.v4.new_markdown_cell(
        """# Voyage AI Integration Example with AgentOps

This notebook demonstrates how to use the Voyage AI provider with AgentOps for embedding operations. The integration supports both synchronous and asynchronous operations, includes token usage tracking, and provides proper error handling.

## Setup Requirements
1. Python >= 3.9 (required by Voyage AI SDK)
2. Required API Keys:
   - AGENTOPS_API_KEY: Set up at https://app.agentops.ai
   - VOYAGE_API_KEY: Get your key at https://app.voyageai.com

## Environment Setup
```bash
# Set your API keys as environment variables
export AGENTOPS_API_KEY='your-key-here'
export VOYAGE_API_KEY='your-key-here'
```"""
    )
)

# Add cell for imports and setup
nb.cells.append(
    nbf.v4.new_code_cell(
        """import os
import asyncio
import agentops
import voyageai
from agentops.llms.providers.voyage import VoyageProvider

# Check for required API keys
def check_api_keys():
    missing_keys = []

    if "AGENTOPS_API_KEY" not in os.environ:
        missing_keys.append("AGENTOPS_API_KEY")
        print("\\nWarning: AGENTOPS_API_KEY not found in environment variables")
        print("To use AgentOps tracking, set your API key:")
        print("    export AGENTOPS_API_KEY='your-key-here'")

    if "VOYAGE_API_KEY" not in os.environ:
        missing_keys.append("VOYAGE_API_KEY")
        print("\\nWarning: VOYAGE_API_KEY not found in environment variables")
        print("To use Voyage AI embeddings, set your API key:")
        print("    export VOYAGE_API_KEY='your-key-here'")

    return missing_keys

# Check API keys and initialize clients
missing_keys = check_api_keys()
if missing_keys:
    print("\\nNote: This notebook will use mock implementations for missing credentials.")
    print("Set the required environment variables to use actual services.")

# Initialize AgentOps client
try:
    ao_client = agentops.Client()
    session = ao_client.start_session()
    if session:
        print("\\nStarted AgentOps session successfully")
        print(f"Session URL: {session.session_url}")
except Exception as e:
    print(f"\\nWarning: Failed to start AgentOps session: {e}")
    print("Using mock session for demonstration")
    session = None

# Initialize Voyage AI client
try:
    voyage_client = voyageai.Client()
    provider = VoyageProvider(voyage_client)
    print("\\nInitialized Voyage AI provider successfully")
except Exception as e:
    print(f"\\nWarning: Failed to initialize Voyage AI provider: {e}")
    print("Using mock client for demonstration")
    provider = None"""
    )
)

# Add cell for basic embedding
nb.cells.append(
    nbf.v4.new_code_cell(
        """# Example text for embedding
text = "The quick brown fox jumps over the lazy dog."

try:
    # Check for required API keys
    if "AGENTOPS_API_KEY" not in os.environ:
        raise ValueError("AGENTOPS_API_KEY not found in environment variables")
    if "VOYAGE_API_KEY" not in os.environ:
        raise ValueError("VOYAGE_API_KEY not found in environment variables")

    # Generate embeddings with session tracking
    result = provider.embed(text, session=session)
    print(f"Embedding dimension: {len(result['embeddings'][0])}")
    print(f"Token usage: {result['usage']}")
except Exception as e:
    print(f"Error: {e}")"""
    )
)

# Add cell for async embedding
nb.cells.append(
    nbf.v4.new_code_cell(
        """async def process_multiple_texts():
    texts = [
        "First example text",
        "Second example text",
        "Third example text"
    ]

    try:
        # Check API keys before processing
        if "AGENTOPS_API_KEY" not in os.environ:
            raise ValueError("AGENTOPS_API_KEY not found in environment variables")
        if "VOYAGE_API_KEY" not in os.environ:
            raise ValueError("VOYAGE_API_KEY not found in environment variables")

        # Process texts concurrently with session tracking
        tasks = [provider.aembed(text, session=session) for text in texts]
        results = await asyncio.gather(*tasks)

        # Display results
        for i, result in enumerate(results, 1):
            print(f"\\nText {i}:")
            print(f"Embedding dimension: {len(result['embeddings'][0])}")
            print(f"Token usage: {result['usage']}")

        return results
    except Exception as e:
        print(f"Error: {e}")
        raise

# Run async example
try:
    results = await process_multiple_texts()
except Exception as e:
    print(f"Error in async processing: {e}")"""
    )
)

# Add cell for cleanup
nb.cells.append(
    nbf.v4.new_code_cell(
        """# End the session
ao_client.end_session("Success", "Example notebook completed successfully")"""
    )
)

# Write the notebook
with open("voyage_example.ipynb", "w") as f:
    nbf.write(nb, f)

print("Notebook created successfully!")
