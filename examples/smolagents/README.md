# Smolagents Examples

This directory contains examples demonstrating how to use Smolagents with AgentOps for agent monitoring and observability.

## Examples

### 1. Simple Task Agent (`simple_task_agent.py`)
A minimal example showing how to create a single agent that can answer questions using web search. This is the best starting point for understanding Smolagents basics.

**Features:**
- Basic agent setup with search capabilities
- AgentOps integration for tracking
- Error handling and session management

### 2. Multi-Agent System (`multi_smolagents_system.py`)
A more complex example demonstrating a hierarchical multi-agent system with:
- Manager agent coordinating multiple specialized agents
- Web search agent with custom tools
- Code interpreter capabilities
- Tool creation and usage

### 3. Text to SQL Agent (`text_to_sql.py`)
An example showing how to create an agent that can convert natural language queries into SQL statements.

## Running the Examples

1. Install dependencies:
```bash
pip install agentops smolagents python-dotenv
```

2. Set up your API keys in a `.env` file:
```env
AGENTOPS_API_KEY=your_agentops_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

3. Run any example:
```bash
python simple_task_agent.py
```

4. View the results in your [AgentOps Dashboard](https://app.agentops.ai/sessions)

## Key Concepts

- **Agents**: AI assistants that can use tools and reason through problems
- **Tools**: Functions that agents can call to interact with external systems
- **Models**: LLM backends via LiteLLM (supports OpenAI, Anthropic, etc.)
- **AgentOps Integration**: Automatic tracking of all agent activities

## Learn More

- [Smolagents Documentation](https://github.com/huggingface/smolagents)
- [AgentOps Documentation](https://docs.agentops.ai)
- [Full Integration Guide](https://docs.agentops.ai/v2/integrations/smolagents)
