import nbformat as nbf

# Create a new notebook
nb = nbf.v4.new_notebook()

# Create markdown cell for introduction
intro_md = """\
# Gemini API Example with AgentOps

This notebook demonstrates how to use AgentOps with Google's Gemini API for both synchronous and streaming text generation."""

# Create code cells
imports = '''\
import google.generativeai as genai
import agentops
from agentops.llms.providers.gemini import GeminiProvider'''

setup = '''\
# Configure the Gemini API
import os

# Replace with your API key
# You can get one at: https://ai.google.dev/tutorials/setup
GEMINI_API_KEY = "YOUR_API_KEY_HERE"  # Replace with your API key
genai.configure(api_key=GEMINI_API_KEY)

# Note: In production, use environment variables:
# import os
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# genai.configure(api_key=GEMINI_API_KEY)'''

init = '''\
# Initialize AgentOps and Gemini model
ao_client = agentops.init()
model = genai.GenerativeModel("gemini-1.5-flash")

# Initialize and override Gemini provider
provider = GeminiProvider(model)
provider.override()'''

sync_test = '''\
# Test synchronous generation
print("Testing synchronous generation:")
response = model.generate_content(
    "What are the three laws of robotics?",
    session=ao_client
)
print(response.text)'''

stream_test = '''\
# Test streaming generation
print("\\nTesting streaming generation:")
response = model.generate_content(
    "Explain the concept of machine learning in simple terms.",
    stream=True,
    session=ao_client
)

for chunk in response:
    print(chunk.text, end="")
print()  # Add newline after streaming output

# Test another synchronous generation
print("\\nTesting another synchronous generation:")
response = model.generate_content(
    "What is the difference between supervised and unsupervised learning?",
    session=ao_client
)
print(response.text)'''

end_session = '''\
# End session and check stats
agentops.end_session(
    end_state="Success",
    end_state_reason="Gemini integration example completed successfully"
)'''

cleanup = '''\
# Clean up
provider.undo_override()'''

# Add cells to notebook
nb.cells.extend([
    nbf.v4.new_markdown_cell(intro_md),
    nbf.v4.new_code_cell(imports),
    nbf.v4.new_code_cell(setup),
    nbf.v4.new_code_cell(init),
    nbf.v4.new_code_cell(sync_test),
    nbf.v4.new_code_cell(stream_test),
    nbf.v4.new_code_cell(end_session),
    nbf.v4.new_code_cell(cleanup)
])

# Write the notebook to a file
with open('examples/gemini_examples/gemini_example_sync.ipynb', 'w') as f:
    nbf.write(nb, f)
