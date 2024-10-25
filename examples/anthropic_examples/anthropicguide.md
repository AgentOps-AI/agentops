# Anthropic and AgentOps

AgentOps supports Anthropic's API for conversing with their LLM backend!

To start, learn more about Antropic [here!](https://www.anthropic.com)
If you want to get down to the gritty details, look [here](https://docs.anthropic.com/en/docs/welcome) for their documentation.


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
> You can download these journals directly and try them on Google Colab or Kaggle!


> [!WARNING]
> Remember; you need to set an API key for both Agentops and Anthropic!


## Sync Example; Nier Storyteller

In this example, we generate a sentence from three parts before having Anthropic generate a short story based off it!

[Access the Journal By Clicking Here](./anthropic-example-sync.ipynb).

## Async Example; Titan Support Protocol

In this example, we generate a script line for a mech based on it's health and the type. At the same time, we generate 4 UUIDs. We finally wait for both functions to finish before printing them for the user.

[Access the Journal By Clicking Here](./anthropic-example-async.ipynb)

## Tool Example; Cyberware

In this example, we have the LLM call a simulated tool which gives one random piece of Cyberware based on the user's requested company. From there, the AI tells the user if the cyberware is good for the user's intended purpose. (combatant, hacker, etc.),

[Access the Journal By Clicking Here](./antrophic-example-tool.ipynb)





## Looking for a Barebones, Straight To The Point Journal?

This journal directly shows the bare basics on using Anthropic and AgentOps!

> [!WARNING]
> This is mainly recommended for those adept at programming or those who already understand how AgentOps and LLM APIs generally work!

[Access the Journal By Clicking Here](./anthropic_example.ipynb)


