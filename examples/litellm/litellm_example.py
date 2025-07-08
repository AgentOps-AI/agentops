# AgentOps for observing LiteLLM
#
# We can use AgentOps to observe LiteLLM, a lightweight library for working with large language models. This integration allows you to monitor and log the performance of your LiteLLM applications, providing insights into their behavior and efficiency.
# LiteLLM integration extends observability to the different agent libraries which rely on LiteLLM and hence make it possible to observe the agents built using these libraries.
#
# [See our LiteLLM docs](https://docs.agentops.ai/v1/integrations/litellm)
# First let's install the required packages
# %pip install -U litellm
# %pip install -U agentops
# %pip install -U python-dotenv
# Then import them
import litellm
import agentops
import os
from dotenv import load_dotenv

# Next, we'll set our API keys. There are several ways to do this, the code below is just the most foolproof way for the purposes of this notebook. It accounts for both users who use environment variables and those who just want to set the API Key here in this notebook.
#
# [Get an AgentOps API key](https://agentops.ai/settings/projects)
#
# 1. Create an environment variable in a .env file or other method. By default, the AgentOps `init()` function will look for an environment variable named `AGENTOPS_API_KEY`. Or...
#
# 2. Replace `<your_agentops_key>` below and pass in the optional `api_key` parameter to the AgentOps `init(api_key=...)` function. Remember not to commit your API key to a public repo!
# LiteLLM allows you to use several models including from OpenAI, Llama, Mistral, Claude, Gemini, Gemma, Dall-E, Whisper, and more all using the OpenAI format. To use a different model all you need to change are the API KEY and model (litellm.completion(model="...")).
load_dotenv()
os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "your_api_key_here")
os.environ["OPENAI_API_KEY"] = os.getenv(
    "OPENAI_API_KEY", "your_openai_api_key_here"
)  # or the provider of your choosing

agentops.init(auto_start_session=False, trace_name="LiteLLM Example")
tracer = agentops.start_trace(trace_name="LiteLLM Example", tags=["litellm-example", "agentops-example"])

# Note: AgentOps requires that you call LiteLLM completions differently than the LiteLLM's docs mention
# Instead of doing this -
#
# ```python
# from litellm import completion
# completion()
# ```
#
# You should do this -
#
# ```python
# import litellm
# litellm.completion()
# ```
messages = [{"role": "user", "content": "Write a 12 word poem about secret agents."}]
response = litellm.completion(model="gpt-4o-mini", messages=messages)  # or the model of your choosing
print(response.choices[0].message.content)

agentops.end_trace(tracer, end_state="Success")

# Let's check programmatically that spans were recorded in AgentOps
print("\n" + "=" * 50)
print("Now let's verify that our LLM calls were tracked properly...")
try:
    agentops.validate_trace_spans(trace_context=tracer)
    print("\n✅ Success! All LLM spans were properly recorded in AgentOps.")
except agentops.ValidationError as e:
    print(f"\n❌ Error validating spans: {e}")
    raise
