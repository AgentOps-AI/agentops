import os
from openai import OpenAI
import agentops
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or "<your_openai_key>"
AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY") or "<your_agentops_key>"

# Initialize AgentOps
agentops.init(AGENTOPS_API_KEY, default_tags=["openai-sync-example"])

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Define system and user prompts
system_prompt = """
You are a master storyteller, with the ability to create vivid and engaging stories.
You have experience in writing for children and adults alike.
You are given a prompt and you need to generate a story based on the prompt.
"""

user_prompt = "Write a story about a cyber-warrior trapped in the imperial time period."

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_prompt},
]

# Generate response
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
)

# Print the generated story
print(response.choices[0].message.content)

# Streaming version
stream = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
    stream=True,
)

for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="")

# End the session
agentops.end_session(end_state="Success", end_state_reason="The story was generated successfully.")
