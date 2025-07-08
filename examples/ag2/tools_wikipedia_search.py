# AG2 Wikipedia Search Tools
#
# AG2's Wikipedia search integration allows agents to perform searches in Wikipedia and retrieve the relevant pages. Follow these steps to integrate Wikipedia Search Tools with AG2 Agents.
#
# Two tools are available for your AG2 agents:
# - `WikipediaQueryRunTool` executes Wikipedia queries and returning summarized page results
# - `WikipediaPageLoadTool` loads the contents of a Wikipedia page together with its metadata (for detailed data extraction)
# # Install required dependencies
# %pip install agentops
# %pip install "ag2[wikipedia, openai]"
# ### Imports
import os
from dotenv import load_dotenv
import agentops
from autogen import AssistantAgent, LLMConfig, UserProxyAgent
from autogen.tools.experimental import WikipediaPageLoadTool, WikipediaQueryRunTool

load_dotenv()
os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "your_api_key_here")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")

# ### Agent Configuration
#
# Configure an assistant agent and user proxy to be used for LLM recommendation and execution respectively.
agentops.init(auto_start_session=False, trace_name="AG2 Wikipedia Search Tools")
tracer = agentops.start_trace(
    trace_name="AG2 Wikipedia Search Tools", tags=["ag2-wikipedia-search-tools", "agentops-example"]
)

config_list = LLMConfig(api_type="openai", model="gpt-4o-mini")

assistant = AssistantAgent(
    name="assistant",
    llm_config=config_list,
)

user_proxy = UserProxyAgent(name="user_proxy", human_input_mode="NEVER", code_execution_config=False)

# ### Query Tool Setup
wikipedia_query_tool = WikipediaQueryRunTool()

# Register the tool for LLM recommendation (assistant agent) and execution (user_proxy agent).
wikipedia_query_tool.register_for_llm(assistant)
wikipedia_query_tool.register_for_execution(user_proxy)

# ### Start the Conversation
#
# With the setup complete, you can now use the assistant to search Wikipedia.
response = user_proxy.initiate_chat(
    recipient=assistant,
    message="Who is the father of AI?",
    max_turns=2,
)

# ## Page Load Tool Setup
# Start by removing the Query tool so we ensure our agent uses the Page Load tool
assistant.remove_tool_for_llm(wikipedia_query_tool)

# Create the Page Load tool
wikipedia_page_load_tool = WikipediaPageLoadTool()

# Register the tool for LLM recommendation (assistant agent) and execution (user_proxy agent).
wikipedia_page_load_tool.register_for_llm(assistant)
wikipedia_page_load_tool.register_for_execution(user_proxy)

response = user_proxy.initiate_chat(
    recipient=assistant,
    message="What's the population of Australia?",
    max_turns=2,
)

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
