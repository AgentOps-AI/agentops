import sys
import warnings
import nbformat as nbf


def create_voyage_example():
    if sys.version_info < (3, 9):
        warnings.warn("Voyage AI SDK requires Python >=3.9. Example may not work correctly.")

    # Create a new notebook
    nb = nbf.v4.new_notebook()

    # Add metadata
    nb.metadata = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}}

    # Create markdown cell with version warning
    markdown_content = """# Using AgentOps with Voyage AI

This notebook demonstrates how to use AgentOps to track Voyage AI embeddings.

> **Note:** Voyage AI SDK requires Python >=3.9. Please ensure you have a compatible Python version installed."""

    markdown_cell = nbf.v4.new_markdown_cell(markdown_content)

    # Create code cell with version check
    code_content = """import sys
if sys.version_info < (3, 9):
    print("Warning: Voyage AI SDK requires Python >=3.9. Example may not work correctly.")

import os
import voyageai
import agentops as ao

# Initialize clients
ao_client = ao.Client()
voyage_client = voyageai.Client()

# Create embeddings
texts = ["Hello world", "How are you?"]
embeddings = voyage_client.embed(texts, model="voyage-3")

# View events in AgentOps dashboard
print(f"View session at: {ao_client.dashboard_url}")"""

    code_cell = nbf.v4.new_code_cell(code_content)

    # Add cells to notebook
    nb.cells = [markdown_cell, code_cell]

    # Save the notebook
    with open("basic_usage.ipynb", "w") as f:
        nbf.write(nb, f)


if __name__ == "__main__":
    create_voyage_example()
