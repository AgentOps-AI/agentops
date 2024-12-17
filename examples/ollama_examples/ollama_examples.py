#!/usr/bin/env python
# coding: utf-8

# # AgentOps Ollama Integration
# 
# This example demonstrates how to use AgentOps to monitor your Ollama LLM calls.
# 
# First let's install the required packages
# 
# > ⚠️ **Important**: Make sure you have Ollama installed and running locally before running this notebook. You can install it from [ollama.ai](https://ollama.com).

# In[ ]:




# Then import them

# In[2]:


import ollama
import agentops
import os
from dotenv import load_dotenv


# Next, we'll set our API keys. For Ollama, we'll need to make sure Ollama is running locally.
# [Get an AgentOps API key](https://agentops.ai/settings/projects)
# 
# 1. Create an environment variable in a .env file or other method. By default, the AgentOps `init()` function will look for an environment variable named `AGENTOPS_API_KEY`. Or...
# 2. Replace `<your_agentops_key>` below and pass in the optional `api_key` parameter to the AgentOps `init(api_key=...)` function. Remember not to commit your API key to a public repo!

# In[3]:


# Let's load our environment variables
load_dotenv()

AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY") or "<your_agentops_key>"


# In[ ]:


# Initialize AgentOps with some default tags
agentops.init(AGENTOPS_API_KEY, default_tags=["ollama-example"])


# Now let's make some basic calls to Ollama. Make sure you have pulled the model first, use the following or replace with whichever model you want to use.

# In[ ]:


ollama.pull("mistral")


# In[ ]:


# Basic completion,
response = ollama.chat(model='mistral',
    messages=[{
        'role': 'user',
        'content': 'What are the benefits of using AgentOps for monitoring LLMs?',
    }]
)
print(response['message']['content'])


# Let's try streaming responses as well

# In[ ]:


# Streaming Example
stream = ollama.chat(
    model='mistral',
    messages=[{
        'role': 'user',
        'content': 'Write a haiku about monitoring AI agents',
    }],
    stream=True
)

for chunk in stream:
    print(chunk['message']['content'], end='')


# In[ ]:


# Conversation Example
messages = [
    {
        'role': 'user',
        'content': 'What is AgentOps?'
    },
    {
        'role': 'assistant',
        'content': 'AgentOps is a monitoring and observability platform for LLM applications.'
    },
    {
        'role': 'user',
        'content': 'Can you give me 3 key features?'
    }
]

response = ollama.chat(
    model='mistral',
    messages=messages
)
print(response['message']['content'])


# > 💡 **Note**: In production environments, you should add proper error handling around the Ollama calls and use `agentops.end_session("Error")` when exceptions occur.

# Finally, let's end our AgentOps session

# In[ ]:


agentops.end_session("Success")

