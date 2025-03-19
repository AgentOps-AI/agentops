# Langchain Callback Handler for AgentOps

This module provides OpenTelemetry-based callback handlers for Langchain that integrate with AgentOps for comprehensive tracing and monitoring of Langchain applications.

## Features

- **Comprehensive Event Tracking**: Monitors all major Langchain operations:
  - LLM calls (including streaming responses)
  - Chat model interactions
  - Chain executions
  - Tool usage
  - Retriever operations
  - Agent actions
  - Retry attempts

- **Dual Mode Support**:
  - Synchronous operations (`LangchainCallbackHandler`)
  - Asynchronous operations (`AsyncLangchainCallbackHandler`)

- **Detailed Span Attributes**:
  - Operation inputs and outputs
  - Token usage statistics
  - Error details and stack traces
  - Model information
  - Tool parameters and results

## Usage

### Basic Usage

```python
from agentops.integrations.langchain.callback_handler import LangchainCallbackHandler

# Initialize the handler
handler = LangchainCallbackHandler(
    api_key="your-api-key"
)

# Use with Langchain
from langchain.llms import OpenAI
from langchain.chains import LLMChain

llm = OpenAI(
    callbacks=[handler],
    temperature=0.7
)

chain = LLMChain(
    llm=llm,
    prompt=your_prompt,
    callbacks=[handler]
)
```

### Async Usage

```python
from agentops.integrations.langchain.callback_handler import AsyncLangchainCallbackHandler

# Initialize the async handler
handler = AsyncLangchainCallbackHandler(
    api_key="your-api-key"
)

# Use with async Langchain
from langchain.llms import OpenAI
from langchain.chains import LLMChain

llm = OpenAI(
    callbacks=[handler],
    temperature=0.7
)

chain = LLMChain(
    llm=llm,
    prompt=your_prompt,
    callbacks=[handler]
)
```

## Span Types and Attributes

### LLM Spans
- **Name**: "llm"
- **Attributes**:
  - `run_id`: Unique identifier for the LLM run
  - `model`: Name of the LLM model
  - `prompt`: Input prompt
  - `response`: Generated response
  - `token_usage`: Token usage statistics

### Chat Model Spans
- **Name**: "chat_model"
- **Attributes**:
  - `run_id`: Unique identifier for the chat run
  - `model`: Name of the chat model
  - `messages`: Conversation history
  - `response`: Generated response

### Chain Spans
- **Name**: "chain"
- **Attributes**:
  - `run_id`: Unique identifier for the chain run
  - `chain_name`: Name of the chain
  - `inputs`: Chain input parameters
  - `outputs`: Chain output results

### Tool Spans
- **Name**: "tool"
- **Attributes**:
  - `run_id`: Unique identifier for the tool run
  - `tool_name`: Name of the tool
  - `tool_input`: Tool input parameters
  - `tool_output`: Tool output results

### Retriever Spans
- **Name**: "retriever"
- **Attributes**:
  - `run_id`: Unique identifier for the retriever run
  - `retriever_name`: Name of the retriever
  - `query`: Search query
  - `documents`: Retrieved documents

### Agent Spans
- **Name**: "agent_action"
- **Attributes**:
  - `run_id`: Unique identifier for the agent run
  - `agent_name`: Name of the agent
  - `tool_input`: Tool input parameters
  - `tool_log`: Agent's reasoning log

## Error Handling

The handler provides comprehensive error tracking:
- Records error type and message
- Preserves error context and stack traces
- Updates span status to ERROR
- Maintains error details in span attributes

## Testing

The handler includes comprehensive tests in `test_callback_handler.py` that verify:
- Basic functionality of both sync and async handlers
- Error handling and recovery
- Span creation and attribute recording
- Token usage tracking
- Streaming response handling
- Chain and tool execution tracking
- Agent action monitoring

To run the tests:
```bash
pytest tests/handlers/langchain/test_callback_handler.py -v
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.