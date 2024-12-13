# CamelAI and AgentOps

AgentOps supports CamelAI's API for conversing with their LLM backend!

To start, learn more about CamelAI [here!](https://www.camel-ai.org)
If you want to get down to the gritty details, look [here](https://docs.camel-ai.org) for their documentation.


> [!NOTE]
> If it's your first time developing for an LLM, be sure to look at our intro to LLMs (coming soon)! Here, we explain generic functions such as giving the AI a memory to exploring novel concepts like summarizing chunks at regular intervals to keep some context while saving memory!

## Getting Started

You can get CamelAI's API working with a few lines of code!

### 1. Import agentops and anthropic to your environment

```python
%pip install camel-ai[all]
%pip install agentops
```

### 2. Setup import statements

```python
import agentops
import os
from getpass import getpass
from dotenv import load_dotenv
```

### 3. Set your API keys

```python
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY") or "<your openai key here>"
agentops_api_key = os.getenv("AGENTOPS_API_KEY") or "<your agentops key here>"
```

From here, you have a number of ways you can interact with the CamelAI API!

## Examples

> [!NOTE]
> You can download these journals directly and try them on Google Colab or Kaggle!


> [!WARNING]
> Remember; you need to set an API key for both Agentops and OpenAI!


## Simple Example; Creating a Bladewolf AI

In this example, we use a csv file to short tune an LLM! We make it sounds like Bladewolf from MGR, before having it give us information.

[Access the Journal By Clicking Here](./camelai-simple-example.ipynb).

## Tool Example; Apex Legends Internet Search

In this example, we look at the tool system within more depth! We will do a search to understand how Apex's melee damage and shields work before determining how many meelee attacks it will take to break a blue shield.

[Access the Journal By Clicking Here](./camelai-multi-agent-example.ipynb)






> [!NOTE]
> If you want to use the tools system, be sure to check their website to find a comprehensive list of the different tools CamelAI supports!


[You can find the tools available here!](https://docs.camel-ai.org/key_modules/tools.html#passing-tools-to-chatagent)







