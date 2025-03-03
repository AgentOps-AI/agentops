import logging
import sys

import openai

import agentops

s = agentops.start_session()

response = openai.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Write a one-line joke"}]
)


breakpoint()
