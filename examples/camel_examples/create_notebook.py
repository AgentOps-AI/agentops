import nbformat as nbf
import json

# Create a new notebook
nb = nbf.v4.new_notebook()

# Title and introduction
nb.cells.append(nbf.v4.new_markdown_cell("""# CAMEL Agent Tracking with AgentOps

This notebook demonstrates how to track CAMEL agents using AgentOps. We'll cover:
1. Setting up CAMEL and AgentOps
2. Running a single agent with tools
3. Running multiple agents with tools

## Installation

First, install the required packages:"""))

# Installation cell
nb.cells.append(nbf.v4.new_code_cell(
"""!pip install "camel-ai[all]==0.2.11"
!pip install agentops"""))

# Setup markdown
nb.cells.append(nbf.v4.new_markdown_cell("""## Setup

Set up your API keys for OpenAI and AgentOps:"""))

# Setup code
nb.cells.append(nbf.v4.new_code_cell(
"""import os
from getpass import getpass

# Set OpenAI API key
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = getpass('Enter your OpenAI API key: ')

# Set AgentOps API key
if "AGENTOPS_API_KEY" not in os.environ:
    os.environ["AGENTOPS_API_KEY"] = getpass('Enter your AgentOps API key: ')"""))

# Single agent markdown
nb.cells.append(nbf.v4.new_markdown_cell("""## Single Agent with Tools

Let's create a single CAMEL agent that uses search tools and track it with AgentOps:"""))

# Single agent code
nb.cells.append(nbf.v4.new_code_cell(
"""import agentops
from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

# Initialize AgentOps
agentops.init(os.getenv("AGENTOPS_API_KEY"), default_tags=["CAMEL Single Agent Example"])

# Import toolkits after AgentOps init for tracking
from camel.toolkits import SearchToolkit

# Set up the agent with search tools
sys_msg = BaseMessage.make_assistant_message(
    role_name='Tools calling operator',
    content='You are a helpful assistant'
)

# Configure tools and model
tools = [*SearchToolkit().get_tools()]
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
)

# Create the agent
camel_agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=tools,
)

# Run the agent
user_msg = 'What is CAMEL-AI.org?'
response = camel_agent.step(user_msg)
print(response)

# End the session
agentops.end_session("Success")"""))

# Multi-agent markdown
nb.cells.append(nbf.v4.new_markdown_cell("""## Multi-Agent with Tools

Now let's create multiple CAMEL agents that can work together and track their interactions:"""))

# Multi-agent code
nb.cells.append(nbf.v4.new_code_cell(
"""import agentops
from typing import List
from camel.agents.chat_agent import FunctionCallingRecord
from camel.societies import RolePlaying
from camel.types import ModelPlatformType, ModelType

# Initialize AgentOps with multi-agent tag
agentops.start_session(tags=["CAMEL Multi-agent Example"])

# Import toolkits after AgentOps init
from camel.toolkits import SearchToolkit, MathToolkit

# Set up your task
task_prompt = (
    "Assume now is 2024 in the Gregorian calendar, "
    "estimate the current age of University of Oxford "
    "and then add 10 more years to this age, "
    "and get the current weather of the city where "
    "the University is located."
)

# Create role-playing agents
assistant_role_name = "Research Assistant"
user_role_name = "Task Requester"

# Configure model
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
)

# Set up tools
tools = [*SearchToolkit().get_tools(), *MathToolkit().get_tools()]

# Create role-playing scenario
role_play = RolePlaying(
    assistant_role_name=assistant_role_name,
    user_role_name=user_role_name,
    task_prompt=task_prompt,
    model=model,
    tools=tools
)

# Start the conversation
chat_history = role_play.chat()

# Print the conversation
for msg in chat_history:
    print(f"{msg.role_name}: {msg.content}\\n")

# End the session
agentops.end_session("Success")"""))

# Results markdown
nb.cells.append(nbf.v4.new_markdown_cell("""## Viewing Results

After running either example, you can view the detailed record of the run in the AgentOps dashboard. The dashboard will show:
1. Agent interactions and messages
2. Tool usage and results
3. LLM calls and responses
4. Session metadata and tags

Visit [app.agentops.ai/drilldown](https://app.agentops.ai/drilldown) to see your agent's performance!"""))

# Set the notebook metadata
nb.metadata = {
    "kernelspec": {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3"
    },
    "language_info": {
        "codemirror_mode": {
            "name": "ipython",
            "version": 3
        },
        "file_extension": ".py",
        "mimetype": "text/x-python",
        "name": "python",
        "nbconvert_exporter": "python",
        "pygments_lexer": "ipython3",
        "version": "3.12"
    }
}

# Write the notebook to a file
with open('camel_example.ipynb', 'w') as f:
    nbf.write(nb, f)
