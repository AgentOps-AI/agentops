import nbformat as nbf

# Create a new notebook
nb = nbf.v4.new_notebook()

# Add title and description
nb.cells.append(
    nbf.v4.new_markdown_cell(
        """# CAMEL Agent Tracking with AgentOps

This notebook demonstrates how to use AgentOps to track and monitor CAMEL agents. We'll cover:
1. Setting up CAMEL with AgentOps
2. Running a single agent example
3. Creating a multi-agent conversation
4. Analyzing session data and costs"""
    )
)

# Add setup and dependency check
nb.cells.append(
    nbf.v4.new_markdown_cell(
        """## Setup

First, let's ensure we have all required packages installed and set up our environment."""
    )
)

# Add dependency installation cell
nb.cells.append(
    nbf.v4.new_code_cell(
        """import sys
import subprocess

def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Install required packages if not present
required_packages = ["camel-ai", "agentops"]
for package in required_packages:
    try:
        __import__(package.replace("-", "_"))
    except ImportError:
        print(f"Installing {package}...")
        install_package(package)
        print(f"{package} installed successfully!")"""
    )
)

# Add imports cell
nb.cells.append(
    nbf.v4.new_code_cell(
        """import os
import agentops
from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.types import ModelPlatformType, ModelType
from camel.models import ModelFactory
import openai

# Helper function to clean API keys
def clean_api_key(key):
    if key:
        return key.strip().strip('"').strip("'")
    return None

# Get and validate API keys
openai_key = clean_api_key(os.getenv("OPENAI_API_KEY"))
agentops_key = clean_api_key(os.getenv("AGENTOPS_API_KEY"))

if not openai_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set")
if not agentops_key:
    raise ValueError("AGENTOPS_API_KEY environment variable is not set")

# Configure OpenAI client
openai.api_key = openai_key
if openai_key.startswith('sk-proj-'):
    openai.api_base = "https://api.openai.com/v1"  # Ensure using standard API endpoint"""
    )
)

# Add description for single agent example
nb.cells.append(
    nbf.v4.new_markdown_cell(
        """## Single Agent Example

Let's create a simple example where we use a single CAMEL agent to explain Python concepts while tracking the interaction with AgentOps."""
    )
)

# Single agent code
nb.cells.append(
    nbf.v4.new_code_cell(
        """# Initialize AgentOps client
ao_client = agentops.Client()
ao_client.configure(api_key=agentops_key)

# Initialize client and start session
try:
    session = ao_client.initialize()
    if not session:
        session = ao_client.start_session(tags=["camel_example", "single_agent"])

    if not session:
        raise RuntimeError("Failed to create AgentOps session")
except Exception as e:
    print(f"Error initializing AgentOps: {e}")
    raise

# Create a tracked version of ChatAgent
class TrackedChatAgent(ChatAgent):
    def __init__(self, system_message, model, name="agent", session=None):
        super().__init__(system_message=system_message, model=model)
        self.name = name
        self.session = session

    def step(self, user_msg):
        try:
            response = super().step(user_msg)
            # Record the interaction with basic parameters
            if self.session:
                try:
                    self.session.record(
                        agentops.LLMEvent(
                            model=str(self.model_backend.model_type),
                            prompt=user_msg,
                            completion=response.msgs[0].content
                        )
                    )
                except Exception as e:
                    print(f"Failed to record event: {e}")
            return response
        except Exception as e:
            print(f"Error during agent step: {e}")
            raise

# Set up the agent
sys_msg = BaseMessage.make_assistant_message(
    role_name="Python Expert",
    content="You are a helpful Python programming expert who can explain concepts clearly and concisely."
)

# Configure model with GPT-3.5
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_3_5_TURBO,
)

# Create the agent with session
camel_agent = TrackedChatAgent(
    system_message=sys_msg,
    model=model,
    name="python_expert",
    session=session
)

# Run the agent
user_msg = "What are Python decorators and how do they work?"
print("User:", user_msg)

response = camel_agent.step(user_msg)
print("\\nAssistant:", response.msgs[0].content)

# Get analytics
print("\\nSession Analytics:")
analytics = session.get_analytics()
print(f"Total Messages: {session.event_counts['llms']}")
print(f"Total Costs: ${session.token_cost:.4f}\\n")

# Print detailed analytics
print("Detailed Analytics:")
for key, value in analytics.items():
    print(f"{key}: {value}")

# End the session
session.end_session(end_state="Success", end_state_reason="Completed CAMEL AI example")"""
    )
)

# Add markdown cell for multi-agent setup
nb.cells.append(
    nbf.v4.new_markdown_cell(
        """## Multi-Agent Conversation

Now let's demonstrate how to track a conversation between two CAMEL agents using AgentOps."""
    )
)

# Add multi-agent code
nb.cells.append(
    nbf.v4.new_code_cell(
        """# Create another agent for multi-agent conversation
sys_msg_2 = BaseMessage.make_assistant_message(
    role_name="Student",
    content="You are a curious student who asks follow-up questions about Python concepts."
)

# Create second agent with session
student_agent = TrackedChatAgent(
    system_message=sys_msg_2,
    model=model,
    name="student",
    session=session
)

# Run multi-agent conversation
print("Starting multi-agent conversation...")
student_msg = "Can you explain more about how to create decorators that accept arguments?"
print("\\nStudent:", student_msg)

expert_response = camel_agent.step(student_msg)
print("\\nPython Expert:", expert_response.msgs[0].content)

student_followup = "Could you provide a practical example of when to use decorators with arguments?"
print("\\nStudent:", student_followup)

expert_final = camel_agent.step(student_followup)
print("\\nPython Expert:", expert_final.msgs[0].content)

# Get final analytics
print("\\nSession Analytics:")
analytics = session.get_analytics()
print(f"Total Messages: {session.event_counts['llms']}")
print(f"Total Costs: ${session.token_cost:.4f}\\n")

# Print detailed analytics
print("Detailed Analytics:")
for key, value in analytics.items():
    print(f"{key}: {value}")

# End the session
session.end_session(end_state="Success", end_state_reason="Completed CAMEL AI example")"""
    )
)

# Add markdown cell for conclusion
nb.cells.append(
    nbf.v4.new_markdown_cell(
        """## Conclusion

In this notebook, we demonstrated how to:
1. Track single-agent CAMEL interactions with AgentOps
2. Monitor multi-agent conversations
3. Collect analytics on message counts and costs
4. Manage different agent roles and personalities

For more information, visit:
- [CAMEL AI Documentation](https://www.camel-ai.org/)
- [AgentOps Dashboard](https://app.agentops.ai/)
- [AgentOps Documentation](https://docs.agentops.ai/)"""
    )
)

# Save the notebook
nb.cells.append(
    nbf.v4.new_markdown_cell(
        """---
Generated with AgentOps - Observability for AI Agents
"""
    )
)

# Set the notebook metadata
nb.metadata = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {
        "codemirror_mode": {"name": "ipython", "version": 3},
        "file_extension": ".py",
        "mimetype": "text/x-python",
        "name": "python",
        "nbconvert_exporter": "python",
        "pygments_lexer": "ipython3",
        "version": "3.12",
    },
}

# Write the notebook to a file
with open("camel_example.ipynb", "w") as f:
    nbf.write(nb, f)
