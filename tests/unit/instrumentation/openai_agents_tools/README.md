# OpenAI Agents Fixture Generator

Dead simple script to grab test fixtures from OpenAI API.

## Usage

```bash
# Activate venv
source .venv/bin/activate

# Run it
python -m tests.unit.instrumentation.openai_agents_tools.generate_fixtures
```

## What it does

- Makes two API calls to OpenAI (normal text and tool calls)
- Saves the JSON responses to `../fixtures/`
- That's it!

## Requirements

- OpenAI API key in env or .env file
- openai + openai-agents packages installed