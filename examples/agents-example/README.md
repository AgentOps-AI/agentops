# OpenAI Agents and AgentOps

AgentOps provides first party support for observing OpenAI's Agents SDK.

Explore [OpenAI's Agents SDK](https://github.com/openai/openai-agents-python) documentation to get started.

> [!NOTE]
> If it's your first time developing with AI agents, these examples will help you understand key concepts like agent lifecycle, tool usage, and dynamic system prompts.

## Getting Started

You can get OpenAI's Agents SDK working with a few lines of code!

### 1. Import agentops and openai-agents to your environment

```python
pip install agentops
pip install openai-agents
```

### 2. Setup import statements

```python
from agents import Agent, Runner
import agentops
import os
from dotenv import load_dotenv
```

### 3. Set your API keys

```python
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY") or "<your_openai_key>"
os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY") or "<your_agentops_key>"
```

### 4. Initialize AgentOps

```python
agentops.init(api_key=os.getenv("AGENTOPS_API_KEY"))
```

From here, you have a number of ways you can interact with the Agents SDK!

## Examples

> [!NOTE]
> You need to set an API key for both AgentOps and OpenAI!

## Basic Agents Example

This example demonstrates how AgentOps automatically instruments the Agents SDK and captures RunResult data with OpenTelemetry semantic conventions.

Access the example [here](./agents_example.py).

## Agent Lifecycle Example

This example shows the complete lifecycle of agents, including:
- Custom agent hooks for monitoring events
- Tool usage with function tools
- Agent handoffs between a starter agent and a multiplier agent
- Structured output using Pydantic models

Access the example [here](./agent_lifecycle_example.py).

## Dynamic System Prompt Example

This example demonstrates how to create agents with dynamic system prompts that change based on context:
- Custom context class to store style information
- Dynamic instructions that adapt based on the context
- Three different response styles: haiku, pirate, and robot

Access the example [here](./dynamic_system_prompt.py).
