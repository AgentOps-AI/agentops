# Gemini Integration Examples

This directory contains examples showing how to use AgentOps with Google's Gemini API.

## Prerequisites

- Python 3.7+
- `agentops` package installed (`pip install -U agentops`)
- `google-generativeai` package installed (`pip install -U google-generativeai`)
- A Gemini API key (get one at [Google AI Studio](https://ai.google.dev/tutorials/setup))
- An AgentOps API key (get one at [AgentOps Dashboard](https://app.agentops.ai/settings/projects))

## Environment Setup

Set your API keys as environment variables:

```bash
export GEMINI_API_KEY='your-gemini-api-key'
export AGENTOPS_API_KEY='your-agentops-api-key'
```

## Examples

### Synchronous and Streaming Example

The [gemini_example_sync.ipynb](./gemini_example_sync.ipynb) notebook demonstrates:
- Basic synchronous text generation
- Streaming text generation
- Automatic event tracking with AgentOps

To run the example:
1. Make sure you have set up your environment variables
2. Open and run the notebook: `jupyter notebook gemini_example_sync.ipynb`
3. View your session in the AgentOps dashboard using the URL printed at the end

## Notes

- The Gemini provider is automatically detected and initialized when you call `agentops.init()`
- No manual provider setup is required
- All LLM calls are automatically tracked and visible in your AgentOps dashboard
- Token usage is extracted from the Gemini API's usage metadata when available
