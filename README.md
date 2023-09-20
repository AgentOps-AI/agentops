# agentops 🕵️

AI agents suck. We’re fixing that.

Build your next agent with evals, observability, and replay analytics. Agentops is the toolkit for evaluating and developing robust and reliable AI agents.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Latest Release 📦
`version: 0.0.4`
This is an alpha release for early testers.

Agentops is still in closed alpha. You can sign up for an API key [here](https://forms.gle/mFAP4XEoaiKXb2Xh9).

# Quick Start

```pip install agentops```

And...

```import agentops as ao```

Documentation: [http://docs.agentops.ai](http://docs.agentops.ai)

### Why Agentops? 🤔

Agent developers often work in the dark, with little to no visibility into agent testing performance. This means their agents never leave the lab. We're changing that. The agentops SDK is designed to become the gold standard for evaluating, grading, and testing agents. Our mission is to make sure your agents are ready for production.

## Evaluations Roadmap 🧭

| Platform | Dashboard | Evals |
|---|---|---|
|✅ Python SDK | ✅ Multi-session and Cross-session metrics | 🚧 Evaluation playground + leaderboard |
|🚧 Evaluation builder API | ✅ Custom event tag tracking | 🔜 Agent scorecards |
|🔜 Javascript/Typescript SDK |  🚧 Session replays| 🔜 Custom eval metrics |


## Debugging Roadmap 🧭

| Performance testing | Environments | LAA (LLM augmented agents) specific tests | Reasoning and execution testing |
|---|---|---|---|
|🔜 Event latency analysis | 🔜 Non-stationary environment testing | 🔜 LLM non-deterministic function detection | 🔜 Infinite loops and recursive thought detection |
|🔜 Regression testing | 🔜 Multi-modal environments | 🔜 Token limit overflow flags | 🔜 Faulty reasoning detection |
|🔜 Success validators (external) | 🔜 Execution containers | 🔜 Context limit overflow flags | 🔜 Generative code validators |
|🔜 Agent controllers/skill tests | 🔜 Honeypot and prompt injection evaluation | 🔜 API bill tracking | 🔜 Error breakpoint analysis |
|🔜 Information context constraint testing | 🔜 Anti-agent roadblocks (i.e. Captchas) | | |
|🔜 Agent workflow execution pricing | | | |

## Agent Arena 🥊
(coming soon!)

# Installation & Usage 📘

To start using Agentops SDK, follow these steps:

1. Clone the GitHub repo:

```bash
git clone https://github.com/AgentOps-AI/agentops.git
```

2. Install the requirements:

```bash
pip install -e agentops/
```

3. Integrate the SDK into your AI agent application. Refer to our [API documentation](http://docs.agentops.ai) for detailed instructions.

# Join the Revolution 🎉

Is there a feature you'd like to see agenotps cover? Just raise it in the issues tab, and we'll work on adding it the roadmap.

We're on a mission to improve AI agents, and we want you to be a part of it. Start building your next agent with agentops SDK today!
