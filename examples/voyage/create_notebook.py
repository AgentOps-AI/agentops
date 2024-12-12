import nbformat as nbf

# Create a new notebook
nb = nbf.v4.new_notebook()

# Add metadata
nb.metadata = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}}

# Create markdown cell
markdown_cell = nbf.v4.new_markdown_cell(
    """# Using AgentOps with Voyage AI

This notebook demonstrates how to use AgentOps to track Voyage AI embeddings."""
)

# Create code cell
code_cell = nbf.v4.new_code_cell(
    """import os
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
)

# Add cells to notebook
nb.cells = [markdown_cell, code_cell]

# Save the notebook
with open("basic_usage.ipynb", "w") as f:
    nbf.write(nb, f)
