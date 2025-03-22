# AgentOps LangChain Callback Handler

This callback handler enables seamless integration between LangChain and AgentOps for tracing and monitoring LLM applications.

## Features

- **Complete Coverage**: Supports all LangChain callback methods 
- **Session Tracking**: Creates a session span that serves as the root for all operations
- **Proper Hierarchy**: Maintains parent-child relationships between operations
- **Complete Instrumentation**: Tracks LLMs, chains, tools, and agent actions
- **Error Tracking**: Records errors from LLMs, chains, and tools
- **Streaming Support**: Handles token streaming for real-time insights
- **Attribute Capture**: Records inputs, outputs, and metadata for all operations
- **Error Resilience**: Handles errors gracefully to ensure spans are always properly closed

## Supported Callbacks

The handler implements all LangChain callback methods:

| Method | Description | Span Kind | Attributes |
|--------|-------------|-----------|------------|
| `on_llm_start` | Start of an LLM call | `llm` | Model, prompts, parameters |
| `on_llm_end` | End of an LLM call | `llm` | Completions, token usage |
| `on_llm_new_token` | Streaming token received | N/A | Token count, last token |
| `on_llm_error` | LLM call error | `llm` | Error details |
| `on_chat_model_start` | Start of a chat model call | `llm` | Model, messages, parameters |
| `on_chain_start` | Start of a chain | `task` | Chain type, inputs |
| `on_chain_end` | End of a chain | `task` | Outputs |
| `on_chain_error` | Chain execution error | `task` | Error details |
| `on_tool_start` | Start of a tool call | `tool` | Tool name, input |
| `on_tool_end` | End of a tool call | `tool` | Output |
| `on_tool_error` | Tool execution error | `tool` | Error details |
| `on_agent_action` | Agent taking an action | `agent` | Tool, input, log |
| `on_agent_finish` | Agent completing a task | `agent` | Output, log |
| `on_text` | Arbitrary text event | `text` | Text content |

All spans have appropriate attributes such as:
- Model information for LLM spans
- Input/output for all operations
- Tool names and types
- Chain types and configurations
- Error details for failed operations

## Troubleshooting

If you're not seeing data in AgentOps:

1. Check that your API key is correctly configured
2. Ensure you're passing the handler to all relevant components
3. Verify that all operations are properly ending/closing

## How It Works

The callback handler:
1. Creates a session span when initialized
2. Intercepts LangChain callbacks for various operations
3. Creates appropriate spans with meaningful attributes
4. Maintains proper parent-child relationships
5. Automatically cleans up and ends spans when operations complete 