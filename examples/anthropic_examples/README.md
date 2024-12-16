# Anthropic and AgentOps

AgentOps provides first party support for observing Anthropic's API.

Explore [Anthropic's](https://www.anthropic.com) documentation [here.](https://docs.anthropic.com/en/docs/welcome) to get started.

> [!NOTE]
> If it's your first time developing for an LLM, be sure to look at our intro to LLMs (coming soon)! Here, we explain generic functions such as giving the AI a memory to exploring novel concepts like summarizing chunks at regular intervals to keep some context while saving memory!

## Getting Started

You can get Anthropic's API working with a few lines of code!

### 1. Import agentops and anthropic to your environment

```python
pip install agentops
pip install anthropic
```

### 2. Setup import statements

```python
from anthropic import Anthropic, AsyncAnthropic
import agentops
import os
from dotenv import load_dotenv
```

### 3. Set your API keys

```python
load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY") or "<your_anthropic_key>"
AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY") or "<your_agentops_key>"
```

From here, you have a number of ways you can interact with the Anthropic API!

## Examples

> [!NOTE]
> You need to set an API key for both Agentops and Anthropic!

## Sync Example - Nier Storyteller

In this example, we generate a sentence from three parts before having Anthropic generate a short story based off it!

Access the example [here.](./anthropic-example-sync.ipynb).

## Async Example - Titan Support Protocol

In this example, we generate a script line for a mech based on it's health and the type. At the same time, we generate 4 UUIDs. We finally wait for both functions to finish before printing them for the user.

Access the example [here.](./anthropic-example-async.ipynb)

## Tool Example - Cyberware

In this example, we have the LLM call a simulated tool which gives one random piece of Cyberware based on the user's requested company. From there, the AI tells the user if the cyberware is good for the user's intended purpose. (combatant, hacker, etc.).

Access the example [here.](./antrophic-example-tool.ipynb)

## Tool Deepdive - VEGA Hell Combat System

In this example, we look at the tool system through a deeper dive; we will use our LLM assistant, VEGA, to get three missions from an API and determine which deserves priority. Then, we will send a number of enemies we want to scan for during combat while also getting our weapons inventory (using two tools at the same time). VEGA will tell us the bet way in which to combat these enemies through a combat strategy.

Access the example [here.](./agentops-anthropic-understanding-tools.ipynb)

> [!NOTE]
> You can explore Anthropic's Tool Calling documentation [here](https://docs.anthropic.com/en/docs/build-with-claude/tool-use) to learn how to use it, some examples and pricing.
