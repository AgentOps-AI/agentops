# OpenAI Test Fixtures Generator

Dead simple script to grab test fixtures from OpenAI APIs.

## Usage

```bash
# Activate venv
source .venv/bin/activate

# Run it
python -m tests.unit.instrumentation.openai_agents_tools.generate_fixtures
```

## What it does

- Makes API calls to OpenAI endpoints:
  - Responses API (standard response + tool calls)
  - Chat Completions API (standard completion + tool calls)
- Saves the JSON responses to `../fixtures/`
- That's it!

## Generated Fixtures

- `openai_response.json` - Standard Responses API response
- `openai_response_tool_calls.json` - Responses API with tool calls
- `openai_chat_completion.json` - Standard Chat Completions API response
- `openai_chat_tool_calls.json` - Chat Completions API with tool calls

## Requirements

- OpenAI API key in env or .env file
- openai + openai-agents packages installed