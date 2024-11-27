# CrewAI and AgentOps for Beginners

## Introduction

In this guide, we’ll explore two groundbreaking tools from the agent development world: **CrewAI**, a multi-agent framework, and **AgentOps**, an agent observability tool. Together, they offer a robust foundation for building and monitoring agent-based applications.

- FYI: This blog has an accompanying video - https://www.youtube.com/watch?v=lfUDYoYMhmY.
- FYI: This blog has an accompanying .git repo - https://github.com/thaddavis/crewai_and_agentops_demo_1 (peep the .git tags)

If you’d like to follow along, ensure you have **Docker Desktop** and **VS Code** installed. Both are free and compatible with macOS, Windows, and Linux. To begin, let's make sure these 2 tools are installed on our machine.

---

### Installing Docker Desktop
1. Visit the [Docker Desktop download page](https://www.docker.com/products/docker-desktop/).
2. Download and install the appropriate version for your system.

### Installing VS Code
1. Visit the [VS Code download page](https://code.visualstudio.com/).
2. Download and install the version matching your system.
3. Launch VS Code and install the following extensions from the Extensions Marketplace:
   - **Docker**
   - **Dev Containers**

---

## Step 1: Setting Up a Dev Container

VIDEO TIMESTAMP: https://www.youtube.com/watch?v=lfUDYoYMhmY&t=150s

1. Create an empty project folder and add the following structure:
```
├── .devcontainer/
|  ├── devcontainer.json
├── Dockerfile.dev
```
2. Add the following content to `devcontainer.json`:
```json
{
  "name": "CrewAI + AgentOps for Beginners",
  "build": {
    "dockerfile": "../Dockerfile.dev"
  },
  "customizations": {
    "vscode": {
        "extensions": [
            "ms-python.python",
            "ms-python.vscode-pylance",
            "ms-python.black-formatter",
            "ms-python.debugpy",
            "ms-azuretools.vscode-docker",
            "shd101wyy.markdown-preview-enhanced"
        ],
        "settings": {}
    }
  },
  "forwardPorts": [],
  "workspaceMount": "source=${localWorkspaceFolder},target=/code,type=bind,consistency=delegated",
  "workspaceFolder": "/code",
  "runArgs": []
}
```
3. Add the following content to Dockerfile.dev:
```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y build-essential
WORKDIR /code # set the working directory
ENV PYTHONPATH=/code
```
4. Launch the container in VS Code:
  - Open the Command Palette (Shift + Command + P on MacOS for example) and search for Dev Containers: Reopen in Container.

After the Dev Container is launched make sure it is working by connecting a terminal and running/testing the following commands...

```sh
python --version
touch main.py
echo "print('Hello World')" > main.py
python main.py
pwd
rm main.py
```

---

## Step 2: Begin building the project

VIDEO TIMESTAMP: https://www.youtube.com/watch?v=lfUDYoYMhmY&t=430s

1. Set up the preliminary project structure:
  ```
  ├── src/
  │   ├── our_crew_of_agents/
  │       ├── main.py
  ```
2. Add the main.py file for preliminary testing:
```sh
mkdir -p src/our_crew_of_agents
touch src/our_crew_of_agents/main.py
```
```python
# src/our_crew_of_agents/main.py
print("Telling my agents to do something...")
```
3. Testing this simple main.py:
```sh
python src/our_crew_of_agents/main.py
```

---

## Step 3: Adding some CrewAI related code

VIDEO TIMESTAMP: https://www.youtube.com/watch?v=lfUDYoYMhmY&t=589s

1. Add the crew.py file:
```sh
touch src/our_crew_of_agents/crew.py
```
```py
# src/our_crew_of_agents/crew.py
from crewai import Crew, Process
from crewai.project import CrewBase, agent, crew

@CrewBase
class OurCrewOfAgents():
	@agent
	def george_washington(self):
		return Agent()
	@agent
	def thomas_jefferson(self):
		return Agent()
	@crew
	def crew(self) -> Crew:
		return Crew(
			agents=self.agents,
			tasks=[],
			process=Process.sequential,
			verbose=True,
		)
```
2. Update the main.py file
```py
# src/our_crew_of_agents/main.py
from src.our_crew_of_agents.crew import OurCrewOfAgents

print("Calling our crew of agents...")
OurCrewOfAgents().crew().kickoff()
```

---

## Step 4: Installing CrewAI

VIDEO TIMESTAMP: https://www.youtube.com/watch?v=lfUDYoYMhmY&t=764s

1. Testing the main.py file
```sh
python src/our_crew_of_agents/main.py
```

⬆️ You should see an error 😜

2. Install CrewAI
```sh
pip install crewai===0.65.2
```

3. Testing the main.py file
```sh
python src/our_crew_of_agents/main.py
```

⬆️ And you should see a DIFFERENT error 🤘

---

## Step 5: Adding agents config

VIDEO TIMESTAMP: https://www.youtube.com/watch?v=lfUDYoYMhmY&t=888s

1. Add the `agents.yaml` file
```sh
mkdir -p src/our_crew_of_agents/config
touch src/our_crew_of_agents/config/agents.yaml
```
```yaml
# src/our_crew_of_agents/config/agents.yaml
george_washington:
  role: >
    American Army General - George Washington
  goal: >
    To lead the American Army to victory in the Revolutionary War.
  backstory: >
    George Washington was born in 1732 in Westmoreland County, Virginia. He was
    the first President of the United States and led the American Army to victory
    in the Revolutionary War. He is known as the "Father of His Country".

thomas_jefferson:
  role: >
    American Founding Father - Thomas Jefferson
  goal: >
    To write the Declaration of Independence and help establish the United States
    as an independent nation.
  backstory: >
    Thomas Jefferson was born in 1743 in Shadwell, Virginia. He was the third
    President of the United States and the principal author of the Declaration of
    Independence. He is known for his role in shaping the early government of the
    United States.
```
2. Update the crew.py file:
```py
# src/our_crew_of_agents/crew.py
from crewai import Crew, Process, Agent
from crewai.project import CrewBase, agent, crew

@CrewBase
class OurCrewOfAgents():
	@agent
	def george_washington(self):
		return Agent(
			config=self.agents_config['george_washington'],
    	verbose=True
		)
	@agent
	def thomas_jefferson(self):
		return Agent(
			config=self.agents_config['thomas_jefferson'],
    	verbose=True
		)
	@crew
	def crew(self) -> Crew:
		return Crew(
			agents=self.agents,
			tasks=[],
			process=Process.sequential,
			verbose=True,
		)
```
3. Try running the crew
```sh
python src/our_crew_of_agents/main.py
```

⬆️ You should see an error 😜

---

## Step 6: Adding tasks config

VIDEO TIMESTAMP: https://youtu.be/lfUDYoYMhmY?si=NkHrf32gT9RIaWk8&t=1063

1. Create the tasks.yaml file
```sh
touch src/our_crew_of_agents/config/tasks.yaml
```
```yaml
# src/our_crew_of_agents/config/tasks.yaml
write_declaration:
    description: >
      Write the Declaration of Independence for the United States during the Revolutionary War.
    expected_output: >
      The Declaration of Independence that will be sent to the British government.
    agent: thomas_jefferson

military_strategy:
    description: >
      Generate a military strategy to defeat the British Army.
    expected_output: >
      A detailed military strategy that will lead the U.S. to victory
    agent: george_washington
```
2. Update the crew.py file
```py
from crewai import Crew, Process, Agent, Task
from crewai.project import CrewBase, agent, crew, task

@CrewBase
class OurCrewOfAgents():
	@agent
	def george_washington(self):
		return Agent(
			config=self.agents_config['george_washington'],
    	verbose=True
		)
	@agent
	def thomas_jefferson(self):
		return Agent(
			config=self.agents_config['thomas_jefferson'],
    	verbose=True
		)
  @task
	def write_declaration(self):
		return Task(
			config=self.tasks_config["write_declaration"],
		)
	@task
	def military_strategy(self):
		return Task(
			config=self.tasks_config["military_strategy"],
		)
	@crew
	def crew(self) -> Crew:
		return Crew(
			agents=self.agents,
			tasks=self.tasks,
			process=Process.sequential,
			verbose=True,
		)
```
3. Run/Test the crew again
```sh
python src/our_crew_of_agents/main.py
```

---

## Step 7: Adding environment variables

VIDEO TIMESTAMP: https://www.youtube.com/watch?v=lfUDYoYMhmY&t=1277s

1. Come over to https://platform.openai.com/
  - Sign up and add some credits to your account
2. Provision an OpenAI API key
3. Copy the API key
4. Add a .env file
```sh
touch .env
```
```txt
# .env
OPENAI_API_KEY=<your_openai_api_key_here>
```
5. Install python-dotenv
```sh
pip install python-dotenv==1.0.1
```
6. Update the main.py file
```py
from dotenv import load_dotenv
load_dotenv()
from src.our_crew_of_agents.crew import OurCrewOfAgents

print("Calling our crew of agents...")
OurCrewOfAgents().crew().kickoff()
```
7. Run the crew
```sh
python src/our_crew_of_agents/main.py
```

⬆️ This should work ✅

---

## Step 8: Adding AgentOps

VIDEO TIMESTAMP: https://www.youtube.com/watch?v=lfUDYoYMhmY&t=1516s

https://www.agentops.ai/

1. Sign up for AgentOps and retrieve your API key from the AgentOps dashboard.
  - https://www.agentops.ai/
  - https://app.agentops.ai/
2. Secure the API key by adding it to the .env file
```txt
# .env
OPENAI_API_KEY=<your_openai_api_key_here>
AGENTOPS_API_KEY=your-agentops-api-key
```
3. Update your main.py to integrate AgentOps
```py
from dotenv import load_dotenv
load_dotenv()
from src.our_crew_of_agents.crew import OurCrewOfAgents

import os
import agentops

agentops.init(os.getenv("AGENTOPS_API_KEY"))

print("Calling our crew of agents...")
OurCrewOfAgents().crew().kickoff()
```
4. Install agentops
```sh
pip install agentops==0.3.12
```

---

## Step 9: Wrapping Up

VIDEO TIMESTAMP: https://www.youtube.com/watch?v=lfUDYoYMhmY&t=1699s

1. Record all dependencies into the requirements.txt file:
```sh
touch requirements.txt
```txt
# requirements.txt
agentops==0.3.12
crewai==0.63.6
python-dotenv==1.0.1

```
2. Create a .gitignore file to exclude sensitive files:
```txt
# .gitignore
.env
```
3. Push your project to GitHub for version control if you like:
```sh
git init
git add -A
git commit -m "Initial commit"
git remote add origin <your-repo-url>
git push -u origin main
```

---

## Conclusion

Congratulations! You've built a functional multi-agent system using CrewAI and integrated observability with AgentOps. This setup ensures your base machine remains uncluttered, while providing robust tools for agent development and monitoring. Experiment further, and let us know you feedback in the comments!
