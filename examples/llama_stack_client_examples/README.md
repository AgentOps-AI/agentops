# TLDR

How to set up a Llama Stack server for supporting the `llama_stack_client_example.ipynb` examples

## Disclaimer

As of 11/2024, Llama Stack is new and is subject to breaking changes.
Here are Llama Stack's docs: https://llama-stack.readthedocs.io/en/latest/

## ToC

1. Running the Ollama Server and Llama Stack Server on the Host 
  - a) Download, install, & start Ollama
  - b) Start the Llama Stack Server
  - c) Call the Llama Stack Server with a Llama Stack Client
2. Running the Ollama Server in a Docker Container

## Running the Ollama Server and Llama Stack Server on the Host 

### 1a - Download, install, & start Ollama

https://ollama.com/

Ollama has an easy-to-use installer available for macOS, Linux, and Windows.

```sh
export OLLAMA_INFERENCE_MODEL="llama3.2:1b-instruct-fp16"
ollama run $OLLAMA_INFERENCE_MODEL --keepalive 60m
ollama run llama3.2:1b --keepalive 60m
```

### 1b - Start the Llama Stack server

You need to configure the Llama Stack server with a yaml config ie: peep the `llama-stack-server-config.yaml` file. FYI, found this config here: `https://github.com/meta-llama/llama-stack/blob/main/llama_stack/templates/ollama/run.yaml`

```sh
export LLAMA_STACK_PORT=5001
export INFERENCE_MODEL="meta-llama/Llama-3.2-1B-Instruct"
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

```sh
docker run \
  -it \
  -p 5001:5001 \
  -v ~/.llama:/root/.llama \
  -v ./examples/llama_stack_client_examples/llama-stack-server-config.yaml:/root/my-run.yaml \
  llamastack/distribution-ollama \
  --yaml-config /root/my-run.yaml \
  --port 5001 \
  --env INFERENCE_MODEL=meta-llama/Llama-3.2-1B \
  --env OLLAMA_URL=http://host.docker.internal:11434
```


### 1c - Call the Llama Stack Server with a Llama Stack Client

ie: Check out the examples in the `llama_stack_client_examples.ipynb` file

## Running the Ollama Server in a Docker Container

```sh - set up the ollama server
docker-compose -f docker.compose.yaml up
```

```sh - download a model
curl -X POST http://localhost:11434/api/pull -d '{"model": "llama3.2:1b"}'
```

```sh - test the model
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2:1b",
  "prompt": "Why is the sky blue?"
}'

curl http://localhost:11434/api/chat -d '{
  "model": "llama3.2:1b",
  "messages": [
    {
      "role": "user",
      "content": "why is the sky blue?"
    }
  ],
  "stream": false
}'
```

## 2 - Running the Ollama Server in a Docker Container

```sh
docker-compose -f docker.compose.yaml up
```

## Common Gotchas

1. Models contain different id's w.r.t. Ollama and Llama Stack. For example, Ollama refers to `Llama-3.2-3B-Instruct` as `llama3.2:1b-instruct-fp16` whereas Llama Stack refers to it as `meta-llama/Llama-3.2-3B-Instruct`

2. Docker will likely need more system memory resources allocated to it

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
- https://llama-stack.readthedocs.io/en/latest/getting_started/index.html
