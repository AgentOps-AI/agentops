# CrewAI Markdown Validator

# First let's install the required packages
# %pip install -U crewai
# %pip install -U agentops
# %pip install -U python-dotenv
# %pip install -U pymarkdownlnt
# Then import them
import sys
from crewai import Agent, Task, LLM
from crewai.tools import tool
import agentops
import os
from pathlib import Path
from dotenv import load_dotenv
from pymarkdown.api import PyMarkdownApi, PyMarkdownApiException

# Next, we'll set our API keys. There are several ways to do this, the code below is just the most foolproof way for the purposes of this notebook. It accounts for both users who use environment variables and those who just want to set the API Key here in this notebook.
# [Get an AgentOps API key](https://agentops.ai/settings/projects)
# 1. Create an environment variable in a .env file or other method. By default, the AgentOps `init()` function will look for an environment variable named `AGENTOPS_API_KEY`. Or...
# 2. Replace `<your_agentops_key>` below and pass in the optional `api_key` parameter to the AgentOps `init(api_key=...)` function. Remember not to commit your API key to a public repo!
load_dotenv()
os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "your_api_key_here")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")

# The first step in any AgentOps integration is to call `agentops.init()`
agentops.init(trace_name="CrewAI Markdown Validator", tags=["markdown_validator", "agentops-example"])


# Lets start by creating our markdown validator tool
@tool("markdown_validation_tool")
def markdown_validation_tool(file_path: str) -> str:
    """
    A tool to review files for markdown syntax errors.

    Returns:
    - validation_results: A list of validation results
    and suggestions on how to fix them.
    """
    print("\n\nValidating Markdown syntax...\n\n" + file_path)
    try:
        if not (os.path.exists(file_path)):
            return "Could not validate file. The provided file path does not exist."
        scan_result = PyMarkdownApi().scan_path(file_path.rstrip().lstrip())
        results = str(scan_result)
        return results  # Return the reviewed document
    except PyMarkdownApiException as this_exception:
        print(f"API Exception: {this_exception}", file=sys.stderr)
        return f"API Exception: {str(this_exception)}"


# Lets create our Agent with CrewAI
default_llm = LLM(
    model="openai/gpt-4o-mini",
    max_tokens=4000,
)

general_agent = Agent(
    role="Requirements Manager",
    goal="""Provide a detailed list of the markdown 
                            linting results. Give a summary with actionable 
                            tasks to address the validation results. Write your 
                            response as if you were handing it to a developer 
                            to fix the issues.
                            DO NOT provide examples of how to fix the issues or
                            recommend other tools to use.""",
    backstory="""You are an expert business analyst 
					and software QA specialist. You provide high quality, 
                    thorough, insightful and actionable feedback via 
                    detailed list of changes and actionable tasks.""",
    allow_delegation=False,
    verbose=True,
    tools=[markdown_validation_tool],
    llm=default_llm,
)

# Now lets create the task for our agent to complete
filename = f"{Path(os.getcwd()).parent.parent.absolute()}/README.md"

syntax_review_task = Task(
    description=f"""
        Use the markdown_validation_tool to review 
        the file(s) at this path: {filename}
        
        Be sure to pass only the file path to the markdown_validation_tool.
        Use the following format to call the markdown_validation_tool:
        Do I need to use a tool? Yes
        Action: markdown_validation_tool
        Action Input: {filename}

        Get the validation results from the tool 
        and then summarize it into a list of changes
        the developer should make to the document.
        DO NOT recommend ways to update the document.
        DO NOT change any of the content of the document or
        add content to it. It is critical to your task to
        only respond with a list of changes.
        
        If you already know the answer or if you do not need 
        to use a tool, return it as your Final Answer.""",
    agent=general_agent,
    expected_output="",
)

# Now lets run our task!
syntax_review_task.execute_sync()


# Let's check programmatically that spans were recorded in AgentOps
print("\n" + "=" * 50)
print("Now let's verify that our LLM calls were tracked properly...")
try:
    agentops.validate_trace_spans(trace_context=None)
    print("\n✅ Success! All LLM spans were properly recorded in AgentOps.")
except agentops.ValidationError as e:
    print(f"\n❌ Error validating spans: {e}")
    raise
