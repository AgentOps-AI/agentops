# TLDR

How to set up a Llama Stack server for supporting the `llama_stack_client_example.ipynb` examples

## Disclaimer

As of 11/2024, Llama Stack is new and is subject to breaking changes.

Here are Llama Stack's docs: https://llama-stack.readthedocs.io/en/latest/

## High-level steps

https://llama-stack.readthedocs.io/en/latest/getting_started/index.html#

1. Download, install, & start Ollama
2. Start the Llama Stack Server
3. Call the Llama Stack Server with a Llama Stack Client

### 1 - Download, install, & start Ollama

https://ollama.com/

Ollama has an easy-to-use installer available for macOS, Linux, and Windows.

```sh
export OLLAMA_INFERENCE_MODEL="llama3.2:3b-instruct-fp16"
ollama run $OLLAMA_INFERENCE_MODEL --keepalive 60m
```

### 2 - Start the Llama Stack server

You need to configure the Llama Stack server with a yaml config ie: peep the `llama-stack-server-config.yaml` file. FYI, found this config here: `https://github.com/meta-llama/llama-stack/blob/main/llama_stack/templates/ollama/run.yaml`

```sh
export LLAMA_STACK_PORT=5001
export INFERENCE_MODEL="meta-llama/Llama-3.2-3B-Instruct"
docker run \
  -it \
  -p $LLAMA_STACK_PORT:$LLAMA_STACK_PORT \
  -v ~/.llama:/root/.llama \
  -v ./examples/llama_stack_client_examples/llama-stack-server-config.yaml:/root/my-run.yaml \
  llamastack/distribution-ollama \
  --yaml-config /root/my-run.yaml \
  --port $LLAMA_STACK_PORT \
  --env INFERENCE_MODEL=$INFERENCE_MODEL \
  --env OLLAMA_URL=http://host.docker.internal:11434
```

### 3 - Call the Llama Stack Server with a Llama Stack Client

ie: Check out the examples in the `llama_stack_client_examples.ipynb` file

## Common Gotchas

1. Models contain different id's w.r.t. Ollama and Llama Stack. For example, Ollama refers to `Llama-3.2-3B-Instruct` as `llama3.2:3b-instruct-fp16` whereas Llama Stack refers to it as `meta-llama/Llama-3.2-3B-Instruct`

## Useful ollama commands

- `ollama list`
- `ollama help`
- `ollama ps`

## Reference links used during development

- https://github.com/meta-llama/llama-stack/blob/main/llama_stack/templates/ollama/run.yaml
- https://llama-stack.readthedocs.io
- https://github.com/meta-llama/llama-stack-client-python
- https://github.com/meta-llama/llama-stack
- download https://ollama.com/
- https://www.llama.com/docs/getting_the_models/meta/
