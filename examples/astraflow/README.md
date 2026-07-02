# Astraflow Examples with AgentOps

This directory contains examples of using [Astraflow](https://www.umodelverse.ai/) (UCloud / 优刻得 umodelverse) with AgentOps instrumentation.

Astraflow is an OpenAI-compatible AI model aggregation platform that provides access to 200+ models through a single API. Because it is OpenAI-compatible, you can use the standard OpenAI Python client by simply pointing it at the Astraflow `base_url`, and AgentOps' built-in OpenAI instrumentation will automatically track every call.

## Prerequisites

- Python >= 3.10 < 3.13
- Install required dependencies:
  ```
  pip install agentops openai python-dotenv
  ```
- Set the appropriate environment variable for your region:
  - **Global endpoint** — `ASTRAFLOW_API_KEY` (base URL: `https://api-us-ca.umodelverse.ai/v1`)
  - **China endpoint** — `ASTRAFLOW_CN_API_KEY` (base URL: `https://api.modelverse.cn/v1`)

## Examples

### Astraflow Example

File: `astraflow_example.py`

Demonstrates basic chat completion usage against Astraflow via the OpenAI client, with full AgentOps tracing.

## AgentOps Integration

These examples show how to use AgentOps to monitor and analyze your AI applications. Because Astraflow is OpenAI-compatible, AgentOps automatically instruments your Astraflow calls through its existing OpenAI integration — no extra configuration required.

To learn more about AgentOps, visit [https://www.agentops.ai](https://www.agentops.ai)
