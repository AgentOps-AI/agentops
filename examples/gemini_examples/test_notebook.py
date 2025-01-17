#!/usr/bin/env python
# coding: utf-8

# # Gemini API Example with AgentOps
#
# This notebook demonstrates how to use AgentOps with Google's Gemini API for both synchronous and streaming text generation.

# In[ ]:


import google.generativeai as genai
import agentops


# In[ ]:


# Configure the Gemini API
import os

# Use environment variable for API key
# Check for API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    print("⚠️ Warning: GEMINI_API_KEY environment variable is not set.")
    print("To run this example, you need to:")
    print("1. Get an API key from https://ai.google.dev/tutorials/setup")
    print("2. Set it as an environment variable: export GEMINI_API_KEY='your-key'")
    import sys

    sys.exit(0)  # Exit gracefully for CI

genai.configure(api_key=GEMINI_API_KEY)


# In[ ]:


# Initialize AgentOps and Gemini model
agentops.init()  # Provider detection happens automatically
model = genai.GenerativeModel("gemini-1.5-flash")


# In[ ]:


# Test synchronous generation
print("Testing synchronous generation:")
response = model.generate_content("What are the three laws of robotics?")
print(response.text)


# In[ ]:


# Test streaming generation
print("\nTesting streaming generation:")
response = model.generate_content("Explain the concept of machine learning in simple terms.", stream=True)

for chunk in response:
    print(chunk.text, end="")
print()  # Add newline after streaming output

# Test another synchronous generation
print("\nTesting another synchronous generation:")
response = model.generate_content("What is the difference between supervised and unsupervised learning?")
print(response.text)


# In[ ]:


# End session and check stats
agentops.end_session(end_state="Success", end_state_reason="Gemini integration example completed successfully")


# In[ ]:


# No cleanup needed - AgentOps handles provider cleanup automatically
