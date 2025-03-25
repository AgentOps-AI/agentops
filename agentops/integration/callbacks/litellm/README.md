# LiteLLM Integration for AgentOps

This integration provides a callback handler for [LiteLLM](https://github.com/BerriAI/litellm) that enables tracing and monitoring of LLM calls through AgentOps.

## Features

- Automatic session span creation and management
- Tracing of all LLM API calls (pre, success, and failure events)
- Support for both synchronous and asynchronous operations
- Detailed span attributes including:
  - Provider information
  - Model details
  - Request parameters (temperature, max_tokens, streaming)
  - Message history
  - Response data
  - Timing information
  - Error details (when applicable)

## Installation

This integration is included with AgentOps. No additional installation is required.

## Usage

```python
from agentops.integration.callbacks.litellm import LiteLLMCallbackHandler
import litellm

# Initialize the callback handler
callback_handler = LiteLLMCallbackHandler(
    api_key="your_agentops_api_key",  # Optional
    tags=["production", "chatbot"],    # Optional
)

# Configure LiteLLM to use the callback
litellm.callbacks = [callback_handler]

# Your LLM calls will now be automatically traced
response = litellm.completion(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Hello, world!"}]
)
```

## Configuration Options

The `LiteLLMCallbackHandler` accepts the following parameters:

- `api_key` (str, optional): Your AgentOps API key
- `tags` (List[str], optional): Tags to add to the session for better organization

## Support

For issues or questions, please refer to:
- [AgentOps Documentation](https://docs.agentops.ai)
- [LiteLLM Documentation](https://docs.litellm.ai) 