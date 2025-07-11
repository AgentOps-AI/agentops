# # Orchestrate a Multi-Agent System
#
# In this notebook, we will make a multi-agent web browser: an agentic system with several agents collaborating to solve problems using the web!
#
# It will be a simple hierarchy, using a `ManagedAgent` object to wrap the managed web search agent:
# ```
# +----------------+
# | Manager agent  |
# +----------------+
#          |
# _________|______________
# |                        |
# Code interpreter   +--------------------------------+
#        tool        |         Managed agent          |
#                    |      +------------------+      |
#                    |      | Web Search agent |      |
#                    |      +------------------+      |
#                    |         |            |         |
#                    |  Web Search tool     |         |
#                    |             Visit webpage tool |
#                    +--------------------------------+
# ```
# Let’s set up this system.
#
# Run the line below to install the required dependencies:
# %pip install markdownify
# %pip install duckduckgo-search
# %pip install smolagents
# %pip install agentops
# 🖇️ Now we initialize the AgentOps client and load the environment variables to use the API keys.
import agentops
from dotenv import load_dotenv
import os
import re
import requests
from markdownify import markdownify
from requests.exceptions import RequestException
from smolagents import tool
from smolagents import LiteLLMModel
from smolagents import (
    CodeAgent,
    ToolCallingAgent,
    DuckDuckGoSearchTool,
)

load_dotenv()
os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "your_api_key_here")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")

agentops.init(auto_start_session=False, trace_name="Smolagents Multi-Agent System")
tracer = agentops.start_trace(
    trace_name="Smolagents Multi-Agent System Orchestration",
    tags=["smolagents", "example", "multi-agent", "agentops-example"],
)
model = LiteLLMModel("openai/gpt-4o-mini")
# ## Create a Web Search Tool
#
# For web browsing, we can already use our pre-existing `DuckDuckGoSearchTool`. However, we will also create a `VisitWebpageTool` from scratch using `markdownify`. Here's how:


@tool
def visit_webpage(url: str) -> str:
    """Visits a webpage at the given URL and returns its content as a markdown string.

    Args:
        url: The URL of the webpage to visit.

    Returns:
        The content of the webpage converted to Markdown, or an error message if the request fails.
    """
    try:
        # Send a GET request to the URL
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes

        # Convert the HTML content to Markdown
        markdown_content = markdownify(response.text).strip()

        # Remove multiple line breaks
        markdown_content = re.sub(r"\\n{3,}", "\\n\\n", markdown_content)

        return markdown_content

    except RequestException as e:
        return f"Error fetching the webpage: {str(e)}"
    except agentops.ValidationError as e:
        return f"An unexpected error occurred: {str(e)}"


# Let’s test our tool:
print(visit_webpage("https://en.wikipedia.org/wiki/Hugging_Face")[:500])
# ## Build Our Multi-Agent System
#
# We will now use the tools `search` and `visit_webpage` to create the web agent.

web_agent = ToolCallingAgent(
    tools=[DuckDuckGoSearchTool(), visit_webpage],
    model=model,
    name="web_research",
    description="Runs web searches for you. Give it your query as an argument. Please NOTE that the argument name is `task`.",
)

manager_agent = CodeAgent(
    tools=[],
    model=model,
    managed_agents=[web_agent],
    additional_authorized_imports=["time", "numpy", "pandas"],
)
# Let’s run our system with the following query:
answer = manager_agent.run(
    "If LLM trainings continue to scale up at the current rhythm until 2030, what would be the electric power in GW required to power the biggest training runs by 2030? What does that correspond to, compared to some countries? Please provide a source for any number used."
)

print(answer)
# Awesome! We've successfully run a multi-agent system. Let's end the agentops session with a "Success" state. You can also end the session with a "Failure" or "Indeterminate" state, which is set as default.
agentops.end_trace(tracer, end_state="Success")

# Let's check programmatically that spans were recorded in AgentOps
print("\n" + "=" * 50)
print("Now let's verify that our LLM calls were tracked properly...")
try:
    agentops.validate_trace_spans(trace_context=tracer)
    print("\n✅ Success! All LLM spans were properly recorded in AgentOps.")
except agentops.ValidationError as e:
    print(f"\n❌ Error validating spans: {e}")
    raise

# You can view the session in the [AgentOps dashboard](https://app.agentops.ai/sessions) by clicking the link provided after ending the session.
