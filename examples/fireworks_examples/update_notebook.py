import nbformat as nbf

# Create a new notebook
nb = nbf.v4.new_notebook()

# Create cells
cells = []

# Cell 1: Imports and initialization
cells.append(
    nbf.v4.new_code_cell(
        """
import os
from dotenv import load_dotenv
from fireworks.client import Fireworks
import agentops
from agentops.enums import EndState

# Load environment variables
load_dotenv()
FIREWORKS_API_KEY = os.getenv("FIREWORKS_API_KEY")

# Initialize AgentOps in development mode
print("Initializing AgentOps in development mode...")
agentops.init(
    api_key=None,  # None for local development
    default_tags=["fireworks-example"]
)
print("Starting new AgentOps session...")
session = agentops.start_session()
print(f"AgentOps initialized. Session URL: {session.session_url}")

# Initialize Fireworks client
print("Initializing Fireworks client...")
client = Fireworks(api_key=FIREWORKS_API_KEY)
print("Fireworks client initialized.")

# Set up messages for story generation
messages = [
    {"role": "system", "content": "You are a creative storyteller."},
    {"role": "user", "content": "Write a short story about a cyber-warrior trapped in the imperial era."}
]
"""
    )
)

# Cell 2: Non-streaming completion
cells.append(
    nbf.v4.new_code_cell(
        """
# Test non-streaming completion
print("Generating story with Fireworks LLM...")
response = client.chat.completions.create(
    model="accounts/fireworks/models/llama-v3p1-8b-instruct",
    messages=messages
)
print("\\nLLM Response:")
print(response.choices[0].message.content)
print("\\nEvent tracking details:")
print(f"Session URL: {session.session_url}")
"""
    )
)

# Cell 3: Streaming completion
cells.append(
    nbf.v4.new_code_cell(
        """
# Test streaming completion
print("\\nGenerating story with streaming enabled...")
stream = client.chat.completions.create(
    model="accounts/fireworks/models/llama-v3p1-8b-instruct",
    messages=messages,
    stream=True
)

print("\\nStreaming LLM Response:")
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
print("\\n\\nEvent tracking details:")
print(f"Session URL: {session.session_url}")
"""
    )
)

# Cell 4: End session with detailed stats
cells.append(
    nbf.v4.new_code_cell(
        """
# End session and show detailed stats
print("\\nEnding AgentOps session...")
try:
    session_stats = session.end_session(
        end_state=EndState.SUCCESS,  # Using the correct enum value
        end_state_reason="Successfully generated stories using both streaming and non-streaming modes."
    )
    print("\\nSession Statistics:")
    if session_stats:
        print(f"Total LLM calls: {session_stats.get('llm_calls', 0)}")
        print(f"Total duration: {session_stats.get('duration', 0):.2f}s")
        print(f"Total cost: ${session_stats.get('cost', 0):.4f}")
        print(f"Session URL: {session.session_url}")
    else:
        print("No session statistics available")
except Exception as e:
    print(f"Error ending session: {str(e)}")
    print("Session URL for debugging:", session.session_url)
"""
    )
)


# Add cells to notebook
nb.cells = cells

# Write the notebook
with open("fireworks_example.ipynb", "w") as f:
    nbf.write(nb, f)
