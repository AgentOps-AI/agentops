# OpenAI Async Example
#
# We are going to create a simple chatbot that creates stories based on a user provided image. The chatbot will use the gpt-4o-mini LLM to generate the story using a user prompt and its vision model to understand the image.
#
# We will track the chatbot with AgentOps and see how it performs!
# First let's install the required packages
# # Install required dependencies
# %pip install agentops
# %pip install openai
# %pip install python-dotenv
# Then import them
from openai import AsyncOpenAI
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
    trace_name="OpenAI Async Example", tags=["openai-async-example", "openai", "agentops-example"]
)
client = AsyncOpenAI()

# And we are all set! Note the seesion url above. We will use it to track the chatbot.
#
# Let's create a simple chatbot that generates stories given an image and a user prompt.
system_prompt = """
You are a master storyteller, with the ability to create vivid and engaging stories.
You have experience in writing for children and adults alike.
You are given a prompt and you need to generate a story based on the prompt.
"""

user_prompt = [
    {"type": "text", "text": "Write a mystery thriller story based on your understanding of the provided image."},
    {
        "type": "image_url",
        "image_url": {"url": "https://www.cosy.sbg.ac.at/~pmeerw/Watermarking/lena_color.gif"},
    },
]

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_prompt},
]


async def main():
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
    )
    print(response.choices[0].message.content)


# await main()


# The response is a string that contains the story. We can track this with AgentOps by navigating to the trace url and viewing the run.
# ## Streaming Version
# We will demonstrate the streaming version of the API.
async def main_stream():
    stream = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        stream=True,
    )
    async for chunk in stream:
        print(chunk.choices[0].delta.content or "", end="")


# await main_stream()
agentops.end_trace(tracer, end_state="Success")

# Note that the response is a generator that yields chunks of the story. We can track this with AgentOps by navigating to the trace url and viewing the run.
# All done!
