# LiteLLM Instrumentation for AgentOps

This module provides comprehensive instrumentation for LiteLLM, enabling automatic telemetry collection for all LLM operations across 100+ providers.

## Overview

The LiteLLM instrumentation uses a **hybrid approach** that combines:
1. **LiteLLM's callback system** for easy integration
2. **Wrapt-based instrumentation** for comprehensive data collection

This approach captures 3-5x more telemetry data than callbacks alone while maintaining the simple user interface.

## Features

### 🚀 Simple Integration
Users only need to add one line:
```python
litellm.success_callback = ["agentops"]
```

### 📊 Comprehensive Telemetry
- **Request attributes**: model, provider, messages, parameters, tokens
- **Response attributes**: content, usage, finish reasons, function calls
- **Streaming metrics**: time-to-first-token, chunk rates, stream duration
- **Error tracking**: detailed error categorization and provider-specific errors
- **Performance metrics**: latencies, token generation rates, costs

### 🔌 Multi-Provider Support
Automatically detects and tracks the underlying provider:
- OpenAI (GPT-4, GPT-3.5, etc.)
- Anthropic (Claude 3, Claude 2, etc.)
- Google (Gemini, PaLM)
- Cohere (Command, Embed)
- Azure OpenAI
- AWS Bedrock
- Hugging Face
- Ollama
- 100+ more providers

### 🎯 Operation Coverage
- Chat completions (`completion`, `acompletion`)
- Embeddings (`embedding`, `aembedding`)
- Image generation (`image_generation`)
- Moderation (`moderation`)
- Streaming responses (with detailed chunk analysis)
- Function/tool calling

## Architecture

### Hybrid Instrumentation Design

```
┌─────────────────────────────────────────────────────────┐
│                    User Application                      │
├─────────────────────────────────────────────────────────┤
│                       LiteLLM                           │
│  ┌─────────────────┐        ┌────────────────────┐    │
│  │ Callback System │───────▶│ AgentOps Callback  │    │
│  └─────────────────┘        └────────────────────┘    │
│           │                           │                 │
│           ▼                           ▼                 │
│  ┌─────────────────┐        ┌────────────────────┐    │
│  │ Internal Methods│◀───────│ Wrapt Instrumentor │    │
│  └─────────────────┘        └────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌────────────────────┐
                    │ OpenTelemetry Spans│
                    └────────────────────┘
```

### Key Components

1. **LiteLLMInstrumentor** (`instrumentor.py`)
   - Main instrumentation class
   - Registers callbacks with LiteLLM
   - Applies wrapt instrumentation to internal methods
   - Manages instrumentation lifecycle

2. **AgentOpsLiteLLMCallback** (`callback_handler.py`)
   - Implements LiteLLM's callback interface
   - Captures basic telemetry through callbacks
   - Works with wrapt for comprehensive data

3. **StreamWrapper** (`stream_wrapper.py`)
   - Wraps streaming responses
   - Captures time-to-first-token
   - Tracks chunk-level metrics
   - Aggregates streaming data

4. **Attribute Extractors** (`attributes/`)
   - Specialized extractors for different operation types
   - Common attributes across all operations
   - Provider-specific attribute handling

## Usage

### Basic Setup

```python
import agentops
import litellm

# Initialize AgentOps (auto-instruments LiteLLM)
agentops.init()

# Enable callbacks
litellm.success_callback = ["agentops"]
litellm.failure_callback = ["agentops"]

# Use LiteLLM normally
response = litellm.completion(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### Streaming Example

```python
# Streaming automatically tracked
stream = litellm.completion(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Tell me a story"}],
    stream=True
)

for chunk in stream:
    print(chunk.choices[0].delta.content, end="")
# Metrics: time-to-first-token, chunk rate, total duration
```

### Multi-Provider Example

```python
# Use any provider through LiteLLM's unified interface
models = [
    "gpt-4",
    "claude-3-opus-20240229",
    "command-nightly",
    "gemini-pro"
]

for model in models:
    response = litellm.completion(
        model=model,
        messages=[{"role": "user", "content": "Hi"}]
    )
    # Provider automatically detected and tracked
```

## Captured Attributes

### Request Attributes
- `llm.vendor`: Always "litellm"
- `llm.provider`: Detected provider (openai, anthropic, etc.)
- `llm.request.model`: Model name
- `llm.request.messages_count`: Number of messages
- `llm.request.temperature`: Temperature setting
- `llm.request.max_tokens`: Max tokens setting
- `llm.request.stream`: Whether streaming is enabled
- And many more...

### Response Attributes
- `llm.response.id`: Response ID
- `llm.response.model`: Actual model used
- `llm.response.choices_count`: Number of choices
- `llm.response.finish_reason`: Completion reason
- `llm.response.content_length`: Response content length
- `llm.usage.*`: Token usage metrics
- And many more...

### Streaming Attributes
- `llm.response.is_streaming`: True for streams
- `llm.response.time_to_first_token`: TTFT metric
- `llm.response.chunk_count`: Total chunks
- `llm.response.chunks_per_second`: Streaming rate
- `llm.response.stream_duration`: Total duration

### Error Attributes
- `llm.error.type`: Error class name
- `llm.error.message`: Error message
- `llm.error.category`: Categorized error type
- `llm.error.provider`: Provider that errored
- `llm.error.status_code`: HTTP status if applicable

## Implementation Details

### Provider Detection

The instrumentation automatically detects the underlying provider from the model name:

```python
# Model patterns for provider detection
"gpt-4" → OpenAI
"claude-3" → Anthropic
"command" → Cohere
"gemini" → Google
"llama" → Meta/Ollama
# And many more...
```

### Cost Estimation

Basic cost estimation is provided for common models:

```python
# Simplified pricing table
"gpt-4": {"prompt": $0.03/1K, "completion": $0.06/1K}
"gpt-3.5-turbo": {"prompt": $0.0015/1K, "completion": $0.002/1K}
"claude-2": {"prompt": $0.008/1K, "completion": $0.024/1K}
```

### Streaming Aggregation

Streaming responses are aggregated to provide complete metrics:

```python
# Aggregated from chunks:
- Total content
- Function calls
- Tool calls
- Token usage
- Finish reasons
```

## Testing

Run the test script to verify instrumentation:

```bash
python test_litellm_instrumentation.py
```

This tests:
- Basic completions
- Streaming responses
- Async operations
- Embeddings
- Function calling
- Error handling
- Multiple providers

## Benefits Over Simple Callbacks

While LiteLLM callbacks provide basic telemetry, our hybrid approach captures:

1. **Detailed Request Analysis**
   - Message role distribution
   - Content length analysis
   - Multi-modal content detection
   - Function/tool configuration

2. **Enhanced Response Tracking**
   - Streaming chunk analysis
   - Time-to-first-token
   - Token generation rates
   - Response aggregation

3. **Provider Intelligence**
   - Automatic provider detection
   - Provider-specific attributes
   - Cross-provider normalization

4. **Performance Insights**
   - Request/response latencies
   - Streaming performance
   - Cost estimation
   - Error categorization

## Future Enhancements

- [ ] Add support for batch operations
- [ ] Implement retry tracking
- [ ] Add model-specific optimizations
- [ ] Enhance cost tracking with real-time pricing
- [ ] Add support for custom providers
- [ ] Implement caching metrics

## Contributing

When adding new features:

1. Update provider patterns in `utils.py`
2. Add attribute extractors in `attributes/`
3. Update the instrumentor for new methods
4. Add tests for new functionality
5. Update this documentation

## License

This instrumentation is part of AgentOps and follows the same license terms.