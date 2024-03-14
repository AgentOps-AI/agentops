<div align="center">
  <img src="logo.png" style="margin: 15px; max-width: 300px" width="50%" alt="Logo">
  <div>
    <a href="https://docs.agentops.ai/introduction">Documentation</a> |
    <a href="https://discord.gg/mKW3ZhN9p2">Discord</a>
    <p><i>AI agents suck. We’re fixing that.</i></p>
  </div>
</div>


Build your next agent with benchmarks, observability, and replay analytics. AgentOps is the toolkit for evaluating and developing robust and reliable AI agents.

AgentOps is open beta. You can sign up for AgentOps [here](https://app.agentops.ai).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) ![PyPI - Version](https://img.shields.io/pypi/v/agentops) <a href="https://pepy.tech/project/agentops">
  <img src="https://static.pepy.tech/badge/agentops/month"> <a href="https://twitter.com/agentopsai">
    <img src="https://img.shields.io/badge/follow-%40agentops-1DA1F2?logo=twitter&style=social" alt="AgentOps Twitter" /> 
  </a>
<a href="https://discord.gg/mKW3ZhN9p2">
    <img src="https://img.shields.io/badge/chat-on%20Discord-blueviolet" alt="Discord community channel" />
  </a>
  <a href="mailto:investor@agentops.ai"><img src="https://img.shields.io/website?color=%23f26522&down_message=Y%20Combinator&label=Not%20Backed%20By&logo=ycombinator&style=flat-square&up_message=Y%20Combinator&url=https%3A%2F%2Fwww.ycombinator.com"></a>
<a href="https://github.com/agentops-ai/agentops/issues">
    <img src="https://img.shields.io/github/commit-activity/m/agentops-ai/agentops" alt="git commit activity" />
  </a>
## Quick Start ⌨️

```pip install agentops```

### Session replays in 3 lines of code
Initialize the AgentOps client, and automatically get analytics on every LLM call.

```python python
import agentops

# Beginning of program's code (i.e. main.py, __init__.py)
ao_client = agentops.Client(<INSERT YOUR API KEY HERE>)

...
# (optional: record specific functions)
@record_function('sample function being record')
def sample_function(...):
    ...

# End of program
ao_client.end_session('Success')
# Woohoo You're done 🎉
```

Refer to our [API documentation](http://docs.agentops.ai) for detailed instructions.

## Time travel debugging 🔮
(coming soon!)

## Agent Arena 🥊
(coming soon!)

## Evaluations Roadmap 🧭

| Platform | Dashboard | Evals |
|---|---|---|
|✅ Python SDK | ✅ Multi-session and Cross-session metrics | ✅ Custom eval metrics |
|🚧 Evaluation builder API | ✅ Custom event tag tracking | 🔜 Agent scorecards |
|✅ [Javascript/Typescript SDK](https://github.com/AgentOps-AI/agentops-node) | ✅ Session replays| 🔜 Evaluation playground + leaderboard|


## Debugging Roadmap 🧭

| Performance testing | Environments | LLM Testing | Reasoning and execution testing |
|---|---|---|---|
|✅ Event latency analysis | 🔜 Non-stationary environment testing | 🔜 LLM non-deterministic function detection | 🚧 Infinite loops and recursive thought detection |
|✅ Agent workflow execution pricing | 🔜 Multi-modal environments | 🚧 Token limit overflow flags | 🔜 Faulty reasoning detection |
|🚧 Success validators (external) | 🔜 Execution containers | 🔜 Context limit overflow flags | 🔜 Generative code validators |
|🔜 Agent controllers/skill tests | ✅ Honeypot and prompt injection detection ([PromptArmor](https://promptarmor.com)) | 🔜 API bill tracking | 🔜 Error breakpoint analysis |
|🔜 Information context constraint testing | 🔜 Anti-agent roadblocks (i.e. Captchas) | 🔜 CI/CD integration checks | |
|🔜 Regression testing | 🔜 Multi-agent framework visualization | | |

## Callback handlers ↩️

### Langchain
AgentOps works seemlessly with applications built using Langchain. To use the handler, install Langchain as an optional dependency:
```shell
pip install agentops[langchain]
```

To use the handler, import and set

```python
import os
from langchain.chat_models import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from agentops.langchain_callback_handler import LangchainCallbackHandler

AGENTOPS_API_KEY = os.environ['AGENTOPS_API_KEY']
handler = LangchainCallbackHandler(api_key=AGENTOPS_API_KEY, tags=['Langchain Example'])

llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY,
                 callbacks=[handler],
                 model='gpt-3.5-turbo')

agent = initialize_agent(tools,
                         llm,
                         agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION,
                         verbose=True,
                         callbacks=[handler], # You must pass in a callback handler to record your agent
                         handle_parsing_errors=True)
```

Check out the [Langchain Examples Notebook](./examples/langchain_examples.ipynb) for more details including Async handlers.

### LlamaIndex 
(Coming Soon)


### Why AgentOps? 🤔

Our mission is to bring your agent from protype to production.

Agent developers often work with little to no visibility into agent testing performance. This means their agents never leave the lab. We're changing that. 

AgentOps is the easiest way to evaluate, grade, and test agents. Is there a feature you'd like to see AgentOps cover? Just raise it in the issues tab, and we'll work on adding it to the roadmap.