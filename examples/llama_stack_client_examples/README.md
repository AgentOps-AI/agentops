# Llama Stack Client Examples

Run Llama Stack with Ollama - either local or containerized.

## Quick Start

Just run:

```bash
./start-stack.sh
```

The script will:
1. Check if Ollama is already running locally
2. Check if Llama Stack server is already running
3. Guide you through what needs to be started

Example outputs:

```bash
# Scenario 1: Ollama running locally
✓ Ollama server is running locally
✗ No Llama Stack server detected
Start Llama Stack server? [Y/n] 

# Scenario 2: Nothing running
✗ No local Ollama server detected
✗ No Llama Stack server detected
No Ollama server detected. Start both Ollama and Llama Stack? [Y/n] 
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
