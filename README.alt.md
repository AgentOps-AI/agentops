# TLDR

Tips for testing Claude Computer Use

## ATTEMPT #1

- added reference to agentops package in the "computer_use_demo" project
- cd computer-use-demo
- docker build . -t computer-use-demo:local

docker build . -t computer-use-demo:local 


- mkdir -p ./computer-use-demo/agentops
- cp -r pyproject.toml ./computer-use-demo/agentops/pyproject.toml
- cp -r agentops ./computer-use-demo/agentops/agentops


## ATTEMPT #2

- mkdir -p ./computer-use-demo/agentops
- cp -r pyproject.toml ./computer-use-demo/agentops/pyproject.toml
- cp -r agentops ./computer-use-demo/agentops/agentops

in computer-use-demo/Dockerfile
  - `COPY --chown=$USERNAME:$USERNAME agentops $HOME/computer_use_demo/agentops` L91
  <!-- - `RUN python -m pip install -U -e $HOME/computer_use_demo/agentops`  -->

- SHIFT + COMMAND + P
- > Dev Containers: Attach to Running Container...

- `pwd` -> `/Users/a/src/projects/11_2024/agentops-ccu/computer-use-demo`

- docker build . -t computer-use-demo:local 
- docker run \
    -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
    -v $(pwd)/computer_use_demo:/home/computeruse/computer_use_demo/ \
    -v $HOME/.anthropic:/home/computeruse/.anthropic \
    -p 5900:5900 \
    -p 8501:8501 \
    -p 6080:6080 \
    -p 8080:8080 \
    -it computer-use-demo:local

## Attempt #3

## TIPS

- sudo apt-get install -y mlocate
- locate -b '\activate' | grep "/home"
- source /home/computeruse/.pyenv/versions/3.11.6/lib/python3.11/venv/scripts/common/activate
- pip list | grep agentops
- 