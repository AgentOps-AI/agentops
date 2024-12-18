import nbformat as nbf

# Create a new notebook
nb = nbf.v4.new_notebook()

# Create cells
cells = []

# Cell 1: Markdown introduction
cells.append(
    nbf.v4.new_markdown_cell(
        """# Fireworks LLM Integration Example

This notebook demonstrates the integration of Fireworks LLM with AgentOps, showcasing both synchronous and asynchronous completions with and without streaming. All examples use the same AgentOps session for proper event tracking."""
    )
)

# Cell 2: Imports and initialization
cells.append(
    nbf.v4.new_code_cell(
        """import os
import logging
import asyncio
from fireworks.client import Fireworks
import agentops
from agentops.enums import EndState
from agentops.llms.providers.fireworks import FireworksProvider
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)"""
    )
)

# Cell 3: Client initialization
cells.append(
    nbf.v4.new_code_cell(
        """# Load environment variables
load_dotenv()
FIREWORKS_API_KEY = os.getenv("FIREWORKS_API_KEY")

if not FIREWORKS_API_KEY:
    raise ValueError("FIREWORKS_API_KEY environment variable is not set")

# Initialize AgentOps client and start session
print("\\nInitializing AgentOps client and starting session...")
ao_client = agentops.Client()
ao_client.initialize()  # Initialize before starting session
session = ao_client.start_session()

if not session:
    raise RuntimeError("Failed to create AgentOps session")

print(f"AgentOps Session URL: {session.session_url}")
print("Session ID:", session.session_id)
print("Session tracking enabled:", bool(session))
print("\\nAll LLM events will be tracked in this session. Watch for event recording messages in the output.")

# Initialize Fireworks client
print("\\nInitializing Fireworks client...")
client = Fireworks(api_key=FIREWORKS_API_KEY)
print("Fireworks client initialized.")

# Initialize and register Fireworks provider
print("\\nRegistering Fireworks provider...")
provider = FireworksProvider(client)
provider.set_session(session)
provider.override()
print("Fireworks provider registered.")"""
    )
)

# Cell 4: Test setup
cells.append(
    nbf.v4.new_markdown_cell(
        """## Test Cases
We'll test four different scenarios:
1. Synchronous non-streaming completion
2. Asynchronous non-streaming completion
3. Synchronous streaming completion
4. Asynchronous streaming completion

All cases will use the same AgentOps session for event tracking."""
    )
)

# Cell 5: Message setup and sync non-streaming test
cells.append(
    nbf.v4.new_code_cell(
        """# Set up messages for story generation
messages = [
    {"role": "system", "content": "You are a creative storyteller."},
    {"role": "user", "content": "Write a short story about a cyber-warrior trapped in the imperial era."},
]

# 1. Test synchronous non-streaming completion
print("1. Generating story with synchronous non-streaming completion...")
response = client.chat.completions.create(
    model="accounts/fireworks/models/llama-v3p1-8b-instruct",
    messages=messages
)
print("\\nSync Non-streaming Response:")
print(response.choices[0].message.content)
print("\\nEvent recorded for sync non-streaming completion")"""
    )
)

# Cell 6: Async non-streaming test
cells.append(
    nbf.v4.new_code_cell(
        """# 2. Test asynchronous non-streaming completion
print("2. Generating story with asynchronous non-streaming completion...")

async def async_completion():
    response = await client.chat.completions.acreate(
        model="accounts/fireworks/models/llama-v3p1-8b-instruct",
        messages=messages
    )
    print("\\nAsync Non-streaming Response:")
    print(response.choices[0].message.content)
    print("\\nEvent recorded for async non-streaming completion")

# Get the current event loop and run the async function
loop = asyncio.get_event_loop()
loop.run_until_complete(async_completion())"""
    )
)

# Cell 7: Sync streaming test
cells.append(
    nbf.v4.new_code_cell(
        """# 3. Test synchronous streaming completion
print("3. Generating story with synchronous streaming...")
stream = client.chat.completions.create(
    model="accounts/fireworks/models/llama-v3p1-8b-instruct",
    messages=messages,
    stream=True
)

print("\\nSync Streaming Response:")
try:
    if asyncio.iscoroutine(stream):
        stream = asyncio.run(stream)
    for chunk in stream:
        if hasattr(chunk, "choices") and chunk.choices and hasattr(chunk.choices[0].delta, "content"):
            content = chunk.choices[0].delta.content
            if content:
                print(content, end="", flush=True)
except Exception as e:
    logger.error(f"Error processing streaming response: {str(e)}")
print()  # New line after streaming"""
    )
)

# Cell 8: Async streaming test
cells.append(
    nbf.v4.new_code_cell(
        """# 4. Test asynchronous streaming completion
print("4. Generating story with asynchronous streaming...")

async def async_streaming():
    try:
        stream = await client.chat.completions.acreate(
            model="accounts/fireworks/models/llama-v3p1-8b-instruct",
            messages=messages,
            stream=True
        )
        print("\\nAsync Streaming Response:")
        async for chunk in stream:
            if hasattr(chunk, "choices") and chunk.choices and hasattr(chunk.choices[0].delta, "content"):
                content = chunk.choices[0].delta.content
                if content:
                    print(content, end="", flush=True)
        print("\\nEvent recorded for async streaming completion")
    except Exception as e:
        logger.error(f"Error in async streaming: {str(e)}")
        raise

# Get the current event loop and run the async function
loop = asyncio.get_event_loop()
loop.run_until_complete(async_streaming())"""
    )
)

# Cell 9: End session and stats
cells.append(
    nbf.v4.new_code_cell(
        """# End session and show detailed stats
print("\\nEnding AgentOps session...")
try:
    print("\\nSession Statistics:")
    session_stats = session.end_session(end_state=EndState.SUCCESS)
    if isinstance(session_stats, dict):
        print(f"Duration: {session_stats.get('duration', 'N/A')}")
        print(f"Cost: ${float(session_stats.get('cost', 0.00)):.2f}")
        print(f"LLM Events: {session_stats.get('llm_events', 0)}")
        print(f"Tool Events: {session_stats.get('tool_events', 0)}")
        print(f"Action Events: {session_stats.get('action_events', 0)}")
        print(f"Error Events: {session_stats.get('error_events', 0)}")
        print(f"Session URL: {session.session_url}")
    else:
        print("No session statistics available")
        print("Session URL for debugging:", session.session_url)
except Exception as e:
    print(f"Error ending session: {str(e)}")
    print("Session URL for debugging:", session.session_url)"""
    )
)

# Add cells to notebook
nb.cells = cells

# Write the notebook
with open("fireworks_example.ipynb", "w") as f:
    nbf.write(nb, f)
