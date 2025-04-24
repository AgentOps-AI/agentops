# Gemini Integration Examples

This directory contains examples demonstrating how to use AgentOps with Google's Gemini API for tracking and monitoring LLM interactions.

## Prerequisites

- Python 3.7+
- `agentops` package installed (`pip install -U agentops`)
- `google-genai` package installed (`pip install -U google-genai>=0.1.0`)
- A Gemini API key (get one at [Google AI Studio](https://ai.google.dev/tutorials/setup))
- An AgentOps API key (get one at [AgentOps Dashboard](https://app.agentops.ai/settings/projects))

## Environment Setup

1. Install required packages:
```bash
pip install -U agentops google-genai
```

2. Set your API keys as environment variables:
```bash
export GEMINI_API_KEY='your-gemini-api-key'
export AGENTOPS_API_KEY='your-agentops-api-key'
```

## Examples

### Synchronous and Streaming Example

The [gemini_example.ipynb](./gemini_example.ipynb) notebook demonstrates:
- Basic synchronous text generation
- Streaming text generation with chunk handling
- Token counting operations
- Automatic event tracking and token usage monitoring
- Session management and statistics

```python
from google import genai
import agentops

# Initialize AgentOps (provider detection is automatic)
agentops.init()

# Create Gemini client
client = genai.Client(api_key='YOUR_GEMINI_API_KEY')

# Generate text (synchronous)
response = client.models.generate_content(
    model="gemini-1.5-flash",
    contents="What are the three laws of robotics?"
)
print(response.text)

# Generate text (streaming)
response_stream = client.models.generate_content_stream(
    model="gemini-1.5-flash",
    contents="Explain machine learning in simple terms."
)
for chunk in response_stream:
    print(chunk.text, end="")

# Token counting
token_response = client.models.count_tokens(
    model="gemini-1.5-flash",
    contents="This is a test sentence to count tokens."
)
print(f"Token count: {token_response.total_tokens}")

# End session and view stats
agentops.end_session(
    end_state="Success",
    end_state_reason="Example completed successfully"
)
```

To run the example:
1. Make sure you have set up your environment variables
2. Open and run the notebook: `jupyter notebook gemini_example.ipynb`
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
