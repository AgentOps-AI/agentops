## How to run Llama Stack server

export LLAMA_STACK_PORT=5001
export INFERENCE_MODEL="meta-llama/Llama-3.2-3B-Instruct"

docker run \
  -it \
  -p $LLAMA_STACK_PORT:$LLAMA_STACK_PORT \
  -v ~/.llama:/root/.llama \
  -v ./run.yaml:/root/my-run.yaml \
  llamastack/distribution-ollama \
  --yaml-config /root/my-run.yaml \
  --port $LLAMA_STACK_PORT \
  --env INFERENCE_MODEL=$INFERENCE_MODEL \
  --env OLLAMA_URL=http://host.docker.internal:11434

## Example Llama Stack server config

https://github.com/meta-llama/llama-stack/blob/main/llama_stack/templates/ollama/run.yaml

## Reference documentation

- https://llama-stack.readthedocs.io/en/latest/getting_started/distributions/self_hosted_distro/ollama.html#setting-up-ollama-server
- https://llama-stack.readthedocs.io/en/latest/getting_started/distributions/self_hosted_distro/ollama.html#running-llama-stack

- https://github.com/meta-llama/llama-stack-client-python
- https://github.com/meta-llama/llama-stack
- download https://ollama.com/
- https://www.llama.com/docs/getting_the_models/meta/

## 