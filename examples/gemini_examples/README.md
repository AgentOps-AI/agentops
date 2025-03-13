# Gemini Integration Examples

This directory contains examples demonstrating how to use AgentOps with Google's Gemini API for tracking and monitoring LLM interactions.

## Prerequisites

- Python 3.7+
- `agentops` package installed (`pip install -U agentops`)
- `google-generativeai` package installed (`pip install -U google-generativeai>=0.1.0`)
- A Gemini API key (get one at [Google AI Studio](https://ai.google.dev/tutorials/setup))
- An AgentOps API key (get one at [AgentOps Dashboard](https://app.agentops.ai/settings/projects))

## Environment Setup

1. Install required packages:
```bash
pip install -U agentops google-generativeai
```

2. Set your API keys as environment variables:
```bash
export GEMINI_API_KEY='your-gemini-api-key'
export AGENTOPS_API_KEY='your-agentops-api-key'
```

## Examples

### Synchronous and Streaming Example

The [gemini_example_sync.ipynb](./gemini_example_sync.ipynb) notebook demonstrates:
- Basic synchronous text generation
- Streaming text generation with chunk handling
- Automatic event tracking and token usage monitoring
- Session management and statistics

```python
import google.generativeai as genai
import agentops

# Configure API keys
genai.configure(api_key=GEMINI_API_KEY)

# Initialize AgentOps (provider detection is automatic)
agentops.init()

# Create Gemini model
model = genai.GenerativeModel("gemini-1.5-flash")

# Generate text (synchronous)
response = model.generate_content("What are the three laws of robotics?")
print(response.text)

# Generate text (streaming)
response = model.generate_content(
    "Explain machine learning in simple terms.",
    stream=True
)
for chunk in response:
    print(chunk.text, end="")

# End session and view stats
agentops.end_session(
    end_state="Success",
    end_state_reason="Example completed successfully"
)
```

To run the example:
1. Make sure you have set up your environment variables
2. Open and run the notebook: `jupyter notebook gemini_example_sync.ipynb`
3. View your session in the AgentOps dashboard using the URL printed at the end

## Features

- **Automatic Provider Detection**: The Gemini provider is automatically detected and initialized when you call `agentops.init()`
- **Zero Configuration**: No manual provider setup required - just import and use
- **Comprehensive Event Tracking**: All LLM calls are automatically tracked and visible in your AgentOps dashboard
- **Token Usage Monitoring**: Token counts are extracted from the Gemini API's usage metadata when available
- **Error Handling**: Robust error handling for both synchronous and streaming responses
- **Session Management**: Automatic session tracking with detailed statistics

## Notes

- The provider supports both synchronous and streaming text generation
- All events are automatically tracked and can be viewed in the AgentOps dashboard
- Token usage is extracted when available in the response metadata
- Error events are automatically captured and logged
- The provider is designed to work seamlessly with AgentOps' session management

## Additional Resources

- [Gemini API Documentation](https://ai.google.dev/docs)
- [AgentOps Documentation](https://docs.agentops.ai)
- [Gemini Integration Guide](https://docs.agentops.ai/v1/integrations/gemini)
