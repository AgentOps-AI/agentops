# AgentOps Langchain Agent Implementation
#
# Using AgentOps monitoring with Langchain is simple. We've created a LangchainCallbackHandler that will do all of the heavy lifting!
#
# First let's install the required packages
# %pip install langchain
# %pip install langchain_openai
# %pip install agentops
# %pip install python-dotenv
# Then import them
import os
from langchain_openai import ChatOpenAI
from langchain.agents import tool, AgentExecutor, create_openai_tools_agent
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate

# The only difference with using AgentOps is that we'll also import this special Callback Handler
from agentops.integration.callbacks.langchain import (
    LangchainCallbackHandler as AgentOpsLangchainCallbackHandler,
)

# Next, we'll set our API keys. There are several ways to do this, the code below is just the most foolproof way for the purposes of this notebook. It accounts for both users who use environment variables and those who just want to set the API Key here in this notebook.
#
# [Get an AgentOps API key](https://agentops.ai/settings/projects)
#
# 1. Create an environment variable in a .env file or other method. By default, the AgentOps `init()` function will look for an environment variable named `AGENTOPS_API_KEY`. Or...
#
# 2. Replace `<your_agentops_key>` below and pass in the optional `api_key` parameter to the AgentOps `init(api_key=...)` function. Remember not to commit your API key to a public repo!
load_dotenv()
os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "your_api_key_here")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")

# This is where AgentOps comes into play. Before creating our LLM instance via Langchain, first we'll create an instance of the AO LangchainCallbackHandler. After the handler is initialized, a session will be recorded automatically.
#
# Pass in your API key, and optionally any tags to describe this session for easier lookup in the AO dashboard.
agentops_handler = AgentOpsLangchainCallbackHandler(tags=["Langchain Example", "agentops-example"])

llm = ChatOpenAI(callbacks=[agentops_handler], model="gpt-3.5-turbo")

# You must pass in a callback handler to record your agent
llm.callbacks = [agentops_handler]

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a helpful assistant. Respond only in Spanish."),
        ("human", "{input}"),
        # Placeholders fill up a **list** of messages
        ("placeholder", "{agent_scratchpad}"),
        # ("tool_names", "find_movie")
    ]
)


# Agents generally use tools. Let's define a simple tool here. Tool usage is also recorded.
@tool
def find_movie(genre: str) -> str:
    """Find available movies"""
    if genre == "drama":
        return "Dune 2"
    else:
        return "Pineapple Express"


tools = [find_movie]

# For each tool, you need to also add the callback handler
for t in tools:
    t.callbacks = [agentops_handler]

# Add the tools to our LLM
llm_with_tools = llm.bind_tools([find_movie])

# Finally, let's create our agent! Pass in the callback handler to the agent, and all the actions will be recorded in the AO Dashboard
agent = create_openai_tools_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools)
agent_executor.invoke({"input": "What comedies are playing?"}, config={"callback": [agentops_handler]})

# ## Check your session
# Finally, check your run on [AgentOps](https://app.agentops.ai). You will see a session recorded with the LLM calls and tool usage.

# Let's check programmatically that spans were recorded in AgentOps
print("\n" + "=" * 50)
print("Now let's verify that our LLM calls were tracked properly...")
try:
    import agentops

    agentops.validate_trace_spans(trace_context=None)
    print("\n✅ Success! All LLM spans were properly recorded in AgentOps.")
except ImportError:
    print("\n❌ Error: agentops library not installed. Please install it to validate spans.")
except agentops.ValidationError as e:
    print(f"\n❌ Error validating spans: {e}")
    raise
