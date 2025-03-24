# OpenAI Agents Test Fixtures Generator

Dead simple script to grab test fixtures from OpenAI Agents API.

## Usage

```bash
# Activate venv
source .venv/bin/activate

# Run it
python -m tests.unit.instrumentation.openai_agents_tools.generate_fixtures
```

## What it does

- Makes API calls to OpenAI Agents endpoint:
  - Standard agent response
  - Agent response with tool calls
- Saves the JSON responses to `../fixtures/`
- That's it!

## Generated Fixtures

- `openai_agents_response.json` - Standard Agents API response
- `openai_agents_tool_response.json` - Agents API with tool calls

## Requirements

- OpenAI API key in env or .env file
- openai + openai-agents packages installed