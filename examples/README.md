# AgentOps Examples

This directory contains comprehensive examples demonstrating how to integrate AgentOps with various AI/ML frameworks, libraries, and providers. Each example is provided as a Jupyter notebook and a Python script with detailed explanations and code samples.

## 📁 Directory Structure

- **[`ag2/`](./ag2/)** - Examples for AG2 (AutoGen 2.0) multi-agent conversations
  - `agentchat_with_memory` - Agent chat with persistent memory
  - `async_human_input` - Asynchronous human input handling
  - `tools_wikipedia_search` - Wikipedia search tool integration

- **[`anthropic/`](./anthropic/)** - Anthropic Claude API integration examples
  - `agentops-anthropic-understanding-tools` - Deep dive into tool usage
  - `anthropic-example-async` - Asynchronous API calls
  - `anthropic-example-sync` - Synchronous API calls
  - `antrophic-example-tool` - Tool calling examples
  - `README.md` - Detailed Anthropic integration guide

- **[`autogen/`](./autogen/)** - Microsoft AutoGen framework examples
  - `AgentChat` - Basic agent chat functionality
  - `MathAgent` - Mathematical problem-solving agent

- **[`crewai/`](./crewai/)** - CrewAI multi-agent framework examples
  - `job_posting` - Job posting automation workflow
  - `markdown_validator` - Markdown validation agent

- **[`gemini/`](./gemini/)** - Google Gemini API integration
  - `gemini_example` - Basic Gemini API usage with AgentOps

- **[`google_adk/`](./google_adk/)** - Google AI Development Kit examples
  - `human_approval` - Human-in-the-loop approval workflows

- **[`langchain/`](./langchain/)** - LangChain framework integration
  - `langchain_examples` - Comprehensive LangChain usage examples

- **[`litellm/`](./litellm/)** - LiteLLM proxy integration
  - `litellm_example` - Multi-provider LLM access through LiteLLM

- **[`openai/`](./openai/)** - OpenAI API integration examples
  - `multi_tool_orchestration` - Complex tool orchestration
  - `openai_example_async` - Asynchronous OpenAI API calls
  - `openai_example_sync` - Synchronous OpenAI API calls
  - `web_search` - Web search functionality

- **[`openai_agents/`](./openai_agents/)** - OpenAI Agents SDK examples
  - `agent_patterns` - Common agent design patterns
  - `agents_tools` - Agent tool integration
  - `customer_service_agent` - Customer service automation

- **[`smolagents/`](./smolagents/)** - SmolAgents framework examples
  - `multi_smolagents_system` - Multi-agent system coordination
  - `text_to_sql` - Natural language to SQL conversion

- **[`watsonx/`](./watsonx/)** - IBM Watsonx AI integration
  - `watsonx-streaming` - Streaming text generation
  - `watsonx-text-chat` - Text generation and chat completion
  - `watsonx-tokeniation-model` - Tokenization and model details
  - `README.md` - Detailed Watsonx integration guide

- **[`xai/`](./xai/)** - xAI (Grok) API integration
  - `grok_examples` - Basic Grok API usage
  - `grok_vision_examples` - Vision capabilities with Grok

### Utility Scripts

- **[`generate_documentation.py`](./generate_documentation.py)** - Script to convert Jupyter notebooks to MDX documentation files
  - Converts notebooks from `examples/` to `docs/v2/examples/`
  - Handles frontmatter, GitHub links, and installation sections
  - Transforms `%pip install` commands to CodeGroup format

## 📓 Prerequisites

1. **AgentOps Account**: Sign up at [agentops.ai](https://agentops.ai)
2. **Python Environment**: Python 3.10+ recommended
3. **API Keys**: Obtain API keys for the services you want to use

## 📖 Documentation Generation

The `generate_documentation.py` script automatically converts these Jupyter notebook examples into documentation for the AgentOps website. It:

- Extracts notebook content and converts to Markdown
- Adds proper frontmatter and metadata
- Transforms installation commands into user-friendly format
- Generates GitHub links for source notebooks
- Creates MDX files in `docs/v2/examples/`

### Usage
```bash
python examples/generate_documentation.py examples/langchain/langchain_examples.ipynb
```

## 🤝 Contributing

When adding new examples:

1. Create a new subdirectory for the framework/provider
2. Include comprehensive Jupyter notebooks with explanations
3. Add a README.md if the integration is complex
4. Ensure examples are self-contained and runnable
5. Follow the existing naming conventions
6. Use the `generate_documentation.py` script to create documentation files
7. Add the example notebook to the main `README.md` for visibility
8. Add the generated documentation to the `docs/v2/examples/` directory for website visibility
9. Submit a pull request with a clear description of your changes

## 📚 Additional Resources

- [AgentOps Documentation](https://docs.agentops.ai)
- [AgentOps Dashboard](https://app.agentops.ai)
- [GitHub Repository](https://github.com/AgentOps-AI/agentops)
- [Community Discord](https://discord.gg/agentops)

## 📄 License

These examples are provided under the same license as the AgentOps project. See the main repository for license details.
