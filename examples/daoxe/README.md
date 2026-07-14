# DaoXE Examples with AgentOps

This directory shows how to call DaoXE through the OpenAI Python client and monitor requests with AgentOps.

DaoXE is a multi-model, multi-protocol API gateway. These examples use the **OpenAI Chat Completions** path:

- Base URL: `https://daoxe.com/v1`
- Auth: `DAOXE_API_KEY`
- Model: account-scoped ID (`DAOXE_MODEL`)

## Prerequisites

- Python >= 3.10 < 3.13
- Install dependencies:

```bash
pip install -r requirements.txt
```

- Environment:

```bash
export DAOXE_API_KEY="your_daoxe_api_key"
export AGENTOPS_API_KEY="your_agentops_api_key"
export DAOXE_MODEL="your_account_model_id"
```

Model IDs depend on your DaoXE account group. Discover them via authenticated `GET /v1/models` or the live catalog at https://daoxe.com/pricing. DaoXE serves customers outside mainland China.

## Examples

### `daoxe_chat_example.py`

- Initializes AgentOps tracing
- Creates `OpenAI(base_url="https://daoxe.com/v1", api_key=DAOXE_API_KEY)`
- Runs a single Chat Completions request
- Ends the trace and validates spans

```bash
python daoxe_chat_example.py
```

## AgentOps Integration

AgentOps instruments the OpenAI client, so Chat Completions traffic routed to DaoXE is captured without custom middleware.

Learn more at https://www.agentops.ai and https://daoxe.com
