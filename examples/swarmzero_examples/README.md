# Web Search Agent

A powerful web search agent built using SwarmZero framework that enables intelligent web searching capabilities.

## Description

This agent utilizes the Tavily API for performing web searches and is built on top of the SwarmZero framework, providing enhanced search capabilities with AI-powered processing.

## Prerequisites

- Python 3.11 or higher
- Poetry package manager
- Tavily API key
- AgentOps API key

## Installation

1. Clone the repository:
```bash
git clone https://github.com/swarmzero/examples.git
cd examples/agents/web-search-agent
```

2. Install dependencies using Poetry:
```bash
poetry install --no-root
```

3. Set up environment variables:
Create a `.env` file in the root directory and add your API keys:
```
TAVILY_API_KEY=your_tavily_api_key_here
AGENTOPS_API_KEY=your_agentops_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

## Usage

1. Activate the Poetry shell:
```bash
poetry shell
```

2. Run the agent:
```bash
poetry run python main.py
```

3. Send a message to the agent:
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/chat' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'user_id=test_user' \
  -F 'session_id=test_web_search_agent' \
  -F 'chat_data={"messages":[{"role":"user","content":"what is swarmzero.ai about?"}]}'
```

4. AgentOps will automatically capture the session:
- View the [agentops.log](agentops.log) file
- See the [AgentOps Dashboard](https://app.agentops.ai/drilldown)

## Dependencies

- `swarmzero`: Main framework for agent development
- `agentops`: Agent operations and monitoring
- `tavily-python`: Web search API client

## Learn more
Visit [SwarmZero](https://swarmzero.ai) to learn more about the SwarmZero framework.
