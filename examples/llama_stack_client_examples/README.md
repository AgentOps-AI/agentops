# Llama Stack Client Examples

The example notebook demonstrates how to use the Llama Stack Client to monitor an Agentic application using AgentOps. We have also provided a `compose.yaml` file to run Ollama in a container.

## Quick Start

First run the following command to start the Ollama server with the Llama Stack client:

```bash
docker compose up
```

Next, run the [notebook](./llama_stack_example.ipynb) to see the waterfall visualization in the [AgentOps](https://app.agentops.ai) dashboard.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LLAMA_STACK_PORT` | Server port | 5001 |
| `INFERENCE_MODEL` | Model ID (must match Llama Stack format) | meta-llama/Llama-3.2-1B-Instruct |
| `OLLAMA_MODEL` | Ollama model ID (must match Ollama format) | llama3.2:1b-instruct-fp16 |
| `SAFETY_MODEL` | Optional safety model | - |
| `NETWORK_MODE` | Docker network mode | auto-configured |
| `OLLAMA_URL` | Ollama API URL | auto-configured |

## Common Gotchas

1. Model naming conventions differ between Ollama and Llama Stack. The same model is referenced differently. For instance, `meta-llama/Llama-3.2-1B-Instruct` in Llama Stack corresponds to `llama3.2:1b-instruct-fp16` in Ollama.

2. Ensure Docker is configured with sufficient system memory allocation to run properly.


## References

- [Download Ollama](https://ollama.com/)
- [Llama Stack Fireworks](./llama_stack_fireworks/README.fireworks.md)
- [Llama Stack Docs](https://llama-stack.readthedocs.io)
- [Ollama Run YAML Template](https://github.com/meta-llama/llama-stack/blob/main/llama_stack/templates/ollama/run.yaml)
- [Llama Stack Documentation](https://llama-stack.readthedocs.io)
- [Llama Stack Client Python](https://github.com/meta-llama/llama-stack-client-python)
- [Llama Stack Repository](https://github.com/meta-llama/llama-stack)
- [Meta Models Documentation](https://www.llama.com/docs/getting_the_models/meta/)
- [Getting Started Guide](https://llama-stack.readthedocs.io/en/latest/getting_started/index.html)
- [Agents Example](https://github.com/meta-llama/llama-stack-apps/blob/main/examples/agents/hello.py)
- [Model Download Reference](https://llama-stack.readthedocs.io/en/latest/references/llama_cli_reference/download_models.html)
