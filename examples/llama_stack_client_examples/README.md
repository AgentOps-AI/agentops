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
| `INFERENCE_MODEL` | Model ID | meta-llama/Llama-3.2-3B-Instruct |
| `SAFETY_MODEL` | Optional safety model | - |
| `NETWORK_MODE` | Docker network mode | auto-configured |
| `OLLAMA_URL` | Ollama API URL | auto-configured |

## Notes

```
llama-stack-client --endpoint http://localhost:$LLAMA_STACK_PORT models list
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ identifier                       ┃ provider_id ┃ provider_resource_id      ┃ metadata ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ meta-llama/Llama-3.2-3B-Instruct │ ollama      │ llama3.2:3b-instruct-fp16 │          │
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

- [Llama Stack Fireworks](./llama_stack_fireworks/README.fireworks.md)
- [Llama Stack Docs](https://llama-stack.readthedocs.io)
- [Ollama](https://ollama.com/)
