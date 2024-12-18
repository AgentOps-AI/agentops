import nbformat as nbf
import logging
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create a new notebook
nb = nbf.v4.new_notebook()
cells = []

# Cell 1: Setup and imports
cells.append(
    nbf.v4.new_code_cell(
        """import nest_asyncio
nest_asyncio.apply()
import os
import logging
import asyncio
import agentops
from fireworks.client import Fireworks
from agentops.llms.providers.fireworks import FireworksProvider

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)"""
    )
)

# Cell 2: Initialize clients
cells.append(
    nbf.v4.new_code_cell(
        """# Check for API keys
if "FIREWORKS_API_KEY" not in os.environ:
    raise ValueError("FIREWORKS_API_KEY environment variable is not set")
if "AGENTOPS_API_KEY" not in os.environ:
    raise ValueError("AGENTOPS_API_KEY environment variable is not set")

# Initialize AgentOps
print("\\nInitializing AgentOps...")
agentops.init(os.getenv("AGENTOPS_API_KEY"), default_tags=["Fireworks Example"])

# Initialize Fireworks client and provider
print("\\nInitializing Fireworks client and provider...")
client = Fireworks()
provider = FireworksProvider(client)
provider.override()
print("Fireworks client and provider initialized.")"""
    )
)

# Cell 3: Set up test messages
cells.append(
    nbf.v4.new_code_cell(
        """# Set up test messages for story generation
messages = [
    {"role": "system", "content": "You are a creative storyteller."},
    {"role": "user", "content": "Write a short story about a cyber-warrior trapped in the imperial era."}
]"""
    )
)

# Cell 4: Sync non-streaming test
cells.append(
    nbf.v4.new_code_cell(
        """# 1. Test synchronous non-streaming completion
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

# Cell 5: Async non-streaming test
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

await async_completion()"""
    )
)

# Cell 6: Sync streaming test
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
for chunk in stream:
    if hasattr(chunk, "choices") and chunk.choices and hasattr(chunk.choices[0].delta, "content"):
        content = chunk.choices[0].delta.content
        if content:
            print(content, end="", flush=True)
print("\\nEvent recorded for sync streaming completion")"""
    )
)

# Cell 7: Async streaming test
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

await async_streaming()"""
    )
)

# Cell 8: End session and stats
cells.append(
    nbf.v4.new_code_cell(
        """# End session and show detailed stats
print("\\nEnding session and showing statistics...")
session_stats = agentops.end_session("Success")
print("\\nSession Statistics:")
print(f"LLM Events: {session_stats.get('llm_events', 0)}")"""
    )
)

# Add cells to notebook
nb.cells = cells

# Write the notebook
with open("fireworks_example.ipynb", "w") as f:
    nbf.write(nb, f)
