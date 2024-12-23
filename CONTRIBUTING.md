# Contributing to AgentOps

Thanks for checking out AgentOps. We're building tools to help developers like you make AI agents that actually work reliably. If you've ever tried to build an agent system, you know the pain - they're a nightmare to debug, impossible to monitor, and when something goes wrong... good luck figuring out why.

We created AgentOps to solve these headaches, and we'd love your help making it even better. Our SDK hooks into all the major Python frameworks (AutoGen, CrewAI, LangChain) and LLM providers (OpenAI, Anthropic, Cohere, etc.) to give you visibility into what your agents are actually doing.

## How You Can Help

There are tons of ways to contribute, and we genuinely appreciate all of them:

1. **Add More Providers**: Help us support new LLM providers. Each one helps more developers monitor their agents.
2. **Improve Framework Support**: Using a framework we don't support yet? Help us add it!
3. **Make Docs Better**: Found our docs confusing? Help us fix them! Clear documentation makes everyone's life easier.
4. **Share Your Experience**: Using AgentOps? Let us know what's working and what isn't. Your feedback shapes our roadmap.

Even if you're not ready to contribute code, we'd love to hear your thoughts. Drop into our Discord, open an issue, or start a discussion. We're building this for developers like you, so your input matters.

## Table of Contents
- [Getting Started](#getting-started)
- [Development Environment](#development-environment)
- [Testing](#testing)
- [Adding LLM Providers](#adding-llm-providers)
- [Code Style](#code-style)
- [Pull Request Process](#pull-request-process)
- [Documentation](#documentation)

## Getting Started

1. **Fork and Clone**:
   First, fork the repository by clicking the 'Fork' button in the top right of the [AgentOps repository](https://github.com/AgentOps-AI/agentops). This creates your own copy of the repository where you can make changes.

   Then clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/agentops.git
   cd agentops
   ```

   Add the upstream repository to stay in sync:
   ```bash
   git remote add upstream https://github.com/AgentOps-AI/agentops.git
   git fetch upstream
   ```

   Before starting work on a new feature:
   ```bash
   git checkout main
   git pull upstream main
   git checkout -b feature/your-feature-name
   ```

2. **Install Dependencies**:
   ```bash
   pip install -e .
   ```

3. **Set Up Pre-commit Hooks**:
   ```bash
   pre-commit install
   ```

## Development Environment

1. **Environment Variables**:
   Create a `.env` file:
   ```
   AGENTOPS_API_KEY=your_api_key
   OPENAI_API_KEY=your_openai_key  # For testing
   ANTHROPIC_API_KEY=your_anthropic_key  # For testing
   # Other keys...
   ```

2. **Virtual Environment**:
   We recommend using `poetry` or `venv`:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Unix
   .\venv\Scripts\activate   # Windows
   ```

3. **Pre-commit Setup**:
   We use pre-commit hooks to automatically format and lint code. Set them up with:
   ```bash
   pip install pre-commit
   pre-commit install
   ```

   That's it! The hooks will run automatically when you commit. To manually check all files:
   ```bash
   pre-commit run --all-files
   ```

## Testing

We maintain comprehensive testing documentation in [tests/README.md](tests/README.md). This includes:

- Test structure and organization
- How to run tests
- Using VCR.py for HTTP interaction testing
- Writing new tests
- Test dependencies and setup

For detailed testing instructions and best practices, please refer to the testing documentation.

## Adding LLM Providers

The `agentops/llms/` directory contains provider implementations. Each provider must:

1. **Inherit from InstrumentedProvider**:
   ```python
   @singleton
   class NewProvider(InstrumentedProvider):
       def __init__(self, client):
           super().__init__(client)
           self._provider_name = "ProviderName"
   ```

2. **Implement Required Methods**:
   - `handle_response()`: Process LLM responses
   - `override()`: Patch the provider's methods
   - `undo_override()`: Restore original methods

3. **Handle Events**:
   Track:
   - Prompts and completions
   - Token usage
   - Timestamps
   - Errors
   - Tool usage (if applicable)

4. **Example Implementation Structure**:
   ```python
   def handle_response(self, response, kwargs, init_timestamp, session=None):
       llm_event = LLMEvent(init_timestamp=init_timestamp, params=kwargs)
       try:
           # Process response
           llm_event.returns = response.model_dump()
           llm_event.prompt = kwargs["messages"]
           # ... additional processing
           self._safe_record(session, llm_event)
       except Exception as e:
           self._safe_record(session, ErrorEvent(trigger_event=llm_event, exception=e))
   ```

## Code Style

1. **Formatting**:
   - Use Black for Python code formatting
   - Maximum line length: 88 characters
   - Use type hints

2. **Documentation**:
   - Docstrings for all public methods
   - Clear inline comments
   - Update relevant documentation

3. **Error Handling**:
   - Use specific exception types
   - Log errors with meaningful messages
   - Include context in error messages

## Pull Request Process

1. **Branch Naming**:
   - `feature/description`
   - `fix/description`
   - `docs/description`

2. **Commit Messages**:
   - Clear and descriptive
   - Reference issues when applicable

3. **PR Requirements**:
   - Pass all tests
   - Maintain or improve code coverage
   - Include relevant documentation
   - Update CHANGELOG.md if applicable

4. **Review Process**:
   - At least one approval required
   - Address all review comments
   - Maintain PR scope

## Documentation

1. **Types of Documentation**:
   - API reference
   - Integration guides
   - Examples
   - Troubleshooting guides

2. **Documentation Location**:
   - Code documentation in docstrings
   - User guides in `docs/`
   - Examples in `examples/`

3. **Documentation Style**:
   - Clear and concise
   - Include code examples
   - Explain the why, not just the what

## Getting Help & Community

We encourage active community participation and are here to help!

### Preferred Communication Channels

1. **GitHub Issues & Discussions**:
   - Open an [issue](https://github.com/AgentOps-AI/agentops/issues) for:
     - Bug reports
     - Feature requests
     - Documentation improvements
   - Start a [discussion](https://github.com/AgentOps-AI/agentops/discussions) for:
     - Questions about usage
     - Ideas for new features
     - Community showcase
     - General feedback

2. **Discord Community**:
   - Join our [Discord server](https://discord.gg/FagdcwwXRR) for:
     - Real-time help
     - Community discussions
     - Feature announcements
     - Sharing your projects

3. **Contact Form**:
   - For private inquiries, use our [contact form](https://agentops.ai/contact)
   - Please note that public channels are preferred for technical discussions

## License

By contributing to AgentOps, you agree that your contributions will be licensed under the MIT License.