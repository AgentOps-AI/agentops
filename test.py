import logging
import sys

import openai

import agentops

agentops.init()

from agentops.logging import logger

logger.setLevel(logging.DEBUG)


response = openai.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Write a one-line joke"}]
)

