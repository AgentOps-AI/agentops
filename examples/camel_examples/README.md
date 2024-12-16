# CamelAI and AgentOps

AgentOps can observe CamelAI's agents in your applications.

To learn more about [CamelAI](https://www.camel-ai.org), check their documentation [here](https://docs.camel-ai.org) to start building your own agents.

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
> You need to set an API key for both Agentops and OpenAI!

## Simple Example - Creating a Bladewolf AI

In this example, we use the [Bladewolf Training Data](https://github.com/AgentOps-AI/agentops/blob/main/examples/camelai_examples/Bladewolf%20Training%20Data%20-%20Sheet1.csv) file to short tune an LLM! We make it sound like Bladewolf from MGR, before having it give us information.

Access the example [here.](https://github.com/AgentOps-AI/agentops/blob/main/examples/camelai_examples/camelai-simple-example.ipynb).

## Tool Example - Apex Legends Internet Search

In this example, we look at the tool system within more depth! We will do a search to understand how Apex's melee damage and shields work before determining how many meelee attacks it will take to break a blue shield.

Access the example [here.](https://github.com/AgentOps-AI/agentops/blob/main/examples/camelai_examples/camelai-multi-agent-example.ipynb)

> [!NOTE]
> CamelAI supports a number of tools that you can use to make your LLM more powerful! You can find the available tools [here!](https://docs.camel-ai.org/key_modules/tools.html#passing-tools-to-chatagent). A Tool Cookbook is also available [here](https://docs.camel-ai.org/cookbooks/agents_with_tools.html) to help you understand how to use them.
