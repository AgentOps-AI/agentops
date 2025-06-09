# IBM Watsonx AI Examples with AgentOps

This directory contains examples of using IBM Watsonx AI with AgentOps instrumentation for various natural language processing tasks.

## Prerequisites

- IBM Watsonx AI account with API key
- Python >= 3.10 < 3.13
- Install required dependencies:
  ```
  pip install agentops ibm-watsonx-ai python-dotenv
  ```

## Environment Setup

Create a `.env` file in your project root with the following values:

```
WATSONX_URL=https://your-region.ml.cloud.ibm.com
WATSONX_API_KEY=your-api-key-here
WATSONX_PROJECT_ID=your-project-id-here
```

## Examples

### 1. Basic Text Generation and Chat Completion

Example: `watsonx-text-chat`
This example demonstrates:
- Basic text generation with IBM Watsonx AI
- Chat completion with system and user messages
- Multiple examples of chat interactions

### 2. Streaming Generation

Example: `watsonx-streaming`

This example demonstrates:
- Streaming text generation
- Streaming chat completion
- Processing streaming responses

### 3. Tokenization and Model Details

Example: `watsonx-tokenization-model`

This example demonstrates:
- Tokenizing text with IBM Watsonx AI models
- Retrieving model details
- Comparing tokenization between different models

## IBM Watsonx AI Models

The examples use the following IBM Watsonx AI models:
- `google/flan-ul2`: A text generation model
- `meta-llama/llama-3-3-70b-instruct`: A chat completion model

You can explore other available models through the IBM Watsonx platform.

## AgentOps Integration

These examples show how to use AgentOps to monitor and analyze your AI applications. AgentOps automatically instruments your IBM Watsonx AI calls to provide insights into performance, usage patterns, and model behavior.

To learn more about AgentOps, visit [https://www.agentops.ai](https://www.agentops.ai)
