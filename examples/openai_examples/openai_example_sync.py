#!/usr/bin/env python
# coding: utf-8

# # OpenAI Sync Example
# 
# We are going to create a simple chatbot that creates stories based on a prompt. The chatbot will use the gpt-4o-mini LLM to generate the story using a user prompt.
# 
# We will track the chatbot with AgentOps and see how it performs!

# First let's install the required packages

# In[ ]:


get_ipython().run_line_magic('pip', 'install -U openai')
get_ipython().run_line_magic('pip', 'install -U agentops')


from openai import OpenAI
import agentops
import os
from dotenv import load_dotenv

# Then continue with the example


# Next, we'll grab our API keys. You can use dotenv like below or however else you like to load environment variables

# In[2]:


load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or "<your_openai_key>"
AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY") or "<your_agentops_key>"


# Next we initialize the AgentOps client.

# In[ ]:


agentops.init(AGENTOPS_API_KEY, default_tags=["openai-sync-example"])


# And we are all set! Note the seesion url above. We will use it to track the chatbot.
# 
# Let's create a simple chatbot that generates stories.

# In[4]:


client = OpenAI(api_key=OPENAI_API_KEY)

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


# In[ ]:


response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
)

print(response.choices[0].message.content)


# The response is a string that contains the story. We can track this with AgentOps by navigating to the session url and viewing the run.

# ## Streaming Version
# We will demonstrate the streaming version of the API.

# In[ ]:


stream = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
    stream=True,
)

for chunk in stream:
  print(chunk.choices[0].delta.content or "", end="")


# Note that the response is a generator that yields chunks of the story. We can track this with AgentOps by navigating to the session url and viewing the run.

# In[ ]:


agentops.end_session(end_state="Success", end_state_reason="The story was generated successfully.")


# We end the session with a success state and a success reason. This is useful if you want to track the success or failure of the chatbot. In that case you can set the end state to failure and provide a reason. By default the session will have an indeterminate end state.
# 
# All done!
