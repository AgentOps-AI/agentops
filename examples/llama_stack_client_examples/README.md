# Llama Stack Client Examples

Run Llama Stack with Ollama - either local or containerized.

## Quick Start

Just run:

```bash
docker compose up
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LLAMA_STACK_PORT` | Server port | 5001 |
| `INFERENCE_MODEL` | Model ID (must match Llama Stack format) | meta-llama/Llama-3.2-1B-Instruct |
| `OLLAMA_MODEL` | Ollama model ID (must match Ollama format) | llama3.2:1b-instruct-fp16 |
| ⚠️ **Important:** | The model IDs must match their respective formats - Ollama and Llama Stack use different naming conventions for the same models | - |
| `SAFETY_MODEL` | Optional safety model | - |
| `NETWORK_MODE` | Docker network mode | auto-configured |
| `OLLAMA_URL` | Ollama API URL | auto-configured |

## Common Gotchas

1. Model naming conventions differ between Ollama and Llama Stack. The same model is referenced differently - for instance, `meta-llama/Llama-3.2-1B-Instruct` in Llama Stack corresponds to `llama3.2:1b-instruct-fp16` in Ollama.

2. Ensure Docker has sufficient system memory allocation to run properly

```
llama-stack-client --endpoint http://localhost:$LLAMA_STACK_PORT models list
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ identifier                       ┃ provider_id ┃ provider_resource_id      ┃ metadata ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ meta-llama/Llama-3.2-1B-Instruct │ ollama      │ llama3.2:1b-instruct-fp16 │          │
└──────────────────────────────────┴─────────────┴───────────────────────────┴──────────┘
```

2. Docker needs sufficient memory allocation

3. Ollama commands:
   ```bash
   ollama list
   ollama help
   ollama ps
   ```

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
