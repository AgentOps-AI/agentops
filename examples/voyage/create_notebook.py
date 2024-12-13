import sys
import warnings
import nbformat as nbf


def create_voyage_example():
    if sys.version_info < (3, 9):
        warnings.warn("Voyage AI SDK requires Python >=3.9. Example may not work correctly.")

    # Create a new notebook
    nb = nbf.v4.new_notebook()

    # Add metadata
    nb.metadata = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {
            "codemirror_mode": {"name": "ipython", "version": 3},
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbconvert_exporter": "python",
            "pygments_lexer": "ipython3",
            "version": "3.9.0",
        },
    }

    # Add introduction
    nb.cells.append(
        nbf.v4.new_markdown_cell(
            """# Voyage AI Integration Example

This notebook demonstrates how to use the Voyage AI provider with AgentOps for embedding operations. The integration supports both synchronous and asynchronous operations, includes token usage tracking, and provides proper error handling.

## Requirements
- Python >= 3.9 (Voyage AI SDK requirement)
- AgentOps library
- Voyage AI API key"""
        )
    )

    # Add setup code
    nb.cells.append(
        nbf.v4.new_code_cell(
            """import os
import asyncio
import voyageai
from agentops.llms.providers.voyage import VoyageProvider

# Set up your Voyage AI API key
os.environ["VOYAGE_API_KEY"] = "your-api-key-here\""""
        )
    )

    # Add provider initialization
    nb.cells.append(
        nbf.v4.new_markdown_cell(
            """## Initialize Voyage AI Provider

First, we'll create a Voyage AI client and initialize the provider:"""
        )
    )

    nb.cells.append(
        nbf.v4.new_code_cell(
            """# Initialize Voyage client and provider
voyage_client = voyageai.Client()
provider = VoyageProvider(voyage_client)

print("Provider initialized successfully!")"""
        )
    )

    # Add basic embedding example
    nb.cells.append(
        nbf.v4.new_markdown_cell(
            """## Basic Embedding Operation

Let's create embeddings for some example text and examine the token usage:"""
        )
    )

    nb.cells.append(
        nbf.v4.new_code_cell(
            """# Example text for embedding
text = "The quick brown fox jumps over the lazy dog."

# Generate embeddings
result = provider.embed(text)

print(f"Embedding dimension: {len(result['embeddings'][0])}")
print(f"Token usage: {result['usage']}")"""
        )
    )

    # Add async embedding example
    nb.cells.append(
        nbf.v4.new_markdown_cell(
            """## Asynchronous Embedding

The provider also supports asynchronous operations for better performance when handling multiple requests:"""
        )
    )

    nb.cells.append(
        nbf.v4.new_code_cell(
            """async def process_multiple_texts():
    texts = [
        "First example text",
        "Second example text",
        "Third example text"
    ]

    # Process texts concurrently
    tasks = [provider.aembed(text) for text in texts]
    results = await asyncio.gather(*tasks)

    return results

# Run async example
results = await process_multiple_texts()

# Display results
for i, result in enumerate(results, 1):
    print(f"\\nText {i}:")
    print(f"Embedding dimension: {len(result['embeddings'][0])}")
    print(f"Token usage: {result['usage']}")"""
        )
    )

    # Add error handling example
    nb.cells.append(
        nbf.v4.new_markdown_cell(
            """## Error Handling

The provider includes proper error handling for various scenarios:"""
        )
    )

    nb.cells.append(
        nbf.v4.new_code_cell(
            """# Example: Handle invalid input
try:
    result = provider.embed(None)
except ValueError as e:
    print(f"Caught ValueError: {e}")

# Example: Handle API errors
try:
    # Temporarily set invalid API key
    os.environ["VOYAGE_API_KEY"] = "invalid-key"
    new_client = voyageai.Client()
    new_provider = VoyageProvider(new_client)
    result = new_provider.embed("test")
except Exception as e:
    print(f"Caught API error: {e}")
finally:
    # Restore original API key
    os.environ["VOYAGE_API_KEY"] = "your-api-key-here\""""
        )
    )

    # Save the notebook
    with open("/home/ubuntu/repos/agentops/examples/voyage/voyage_example.ipynb", "w") as f:
        nbf.write(nb, f)


if __name__ == "__main__":
    create_voyage_example()
