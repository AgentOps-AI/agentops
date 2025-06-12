# OpenAI Sync Example
#
# We are going to create a simple chatbot that creates stories based on a prompt. The chatbot will use the gpt-4o-mini LLM to generate the story using a user prompt.
#
# We will track the chatbot with AgentOps and see how it performs!
# First let's install the required packages
# # Install required dependencies
# %pip install agentops
# %pip install openai
# %pip install python-dotenv
# Then import them
from openai import OpenAI
import agentops
import os
from dotenv import load_dotenv

# Next, we'll grab our API keys. You can use dotenv like below or however else you like to load environment variables
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")
os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "your_api_key_here")

# Next we initialize the AgentOps client.
agentops.init(auto_start_session=True)
tracer = agentops.start_trace(
    trace_name="OpenAI Sync Example", tags=["openai-sync-example", "openai", "agentops-example"]
)
client = OpenAI()

# And we are all set! Note the seesion url above. We will use it to track the chatbot.
#
# Let's create a simple chatbot that generates stories.
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

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
)

print(response.choices[0].message.content)

# The response is a string that contains the story. We can track this with AgentOps by navigating to the trace url and viewing the run.
# ## Streaming Version
# We will demonstrate the streaming version of the API.
stream = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
    stream=True,
)

for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="")

agentops.end_trace(tracer, end_state="Success")

# Note that the response is a generator that yields chunks of the story. We can track this with AgentOps by navigating to the trace url and viewing the run.
# All done!
