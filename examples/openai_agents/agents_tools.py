# OpenAI Agents Tools Demonstration
#
# This notebook demonstrates various tools available in the Agents SDK and how AgentOps provides observability for tool usage.
#
# ## General Flow
#
# This notebook will walk you through several key tools:
#
# 1. **Code Interpreter Tool** - Execute Python code and perform mathematical calculations
# 2. **File Search Tool** - Search through vector stores and documents
# 3. **Image Generation Tool** - Generate images from text descriptions
# 4. **Web Search Tool** - Search the web for current information
#
# Each tool demonstrates how AgentOps automatically tracks tool usage, providing insights into performance, costs, and effectiveness.
# ## Prerequisites
#
# Before running this notebook, you'll need:
#
# 1. **AgentOps Account**: Create a free account at [app.agentops.ai](https://app.agentops.ai)
# 2. **AgentOps API Key**: Obtain your API key from your AgentOps dashboard
# 3. **OpenAI API Key**: Get your API key from [platform.openai.com](https://platform.openai.com)
# 4. **Vector Store ID**: Configure it from [platform.openai.com](https://platform.openai.com).
# # Install required packages
# %pip install agentops
# %pip install openai-agents
# %pip install pydotenv
# Set the API keys for your AgentOps and OpenAI accounts.
import os
from dotenv import load_dotenv
import agentops
import base64
import subprocess
import sys
import tempfile
import asyncio

from agents import (
    Agent,
    CodeInterpreterTool,
    FileSearchTool,
    ImageGenerationTool,
    Runner,
    WebSearchTool,
    trace,
)

load_dotenv()

os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "your_api_key_here")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")

agentops.init(
    auto_start_session=False,
    trace_name="OpenAI Agents Tools Examples",
    tags=["openai-agents", "tools", "agentops-example"],
)
tracer = agentops.start_trace(
    trace_name="OpenAI Agents Tools Examples",
    tags=["openai-agents", "tools", "agentops-example"],
)

# ## 1. Code Interpreter Tool
#
# The Code Interpreter Tool allows agents to execute Python code in a secure environment. This is particularly useful for mathematical calculations, data analysis, and generating visualizations.
#
# **Key Features:**
# - Execute Python code safely
# - Perform complex mathematical calculations
# - Generate plots and visualizations
# - Handle data processing tasks
# Code Interpreter Tool Example


async def run_code_interpreter_demo():
    agent = Agent(
        name="Code interpreter",
        instructions="You love doing math.",
        tools=[
            CodeInterpreterTool(
                tool_config={"type": "code_interpreter", "container": {"type": "auto"}},
            )
        ],
    )

    with trace("Code interpreter example"):
        print("Solving math problem...")
        result = Runner.run_streamed(agent, "What is the square root of 273 * 312821 plus 1782?")
        async for event in result.stream_events():
            if (
                event.type == "run_item_stream_event"
                and event.item.type == "tool_call_item"
                and event.item.raw_item.type == "code_interpreter_call"
            ):
                print(f"Code interpreter code:\n```\n{event.item.raw_item.code}\n```\n")
            elif event.type == "run_item_stream_event":
                print(f"Other event: {event.item.type}")

        print(f"Final output: {result.final_output}")


# Run the demo
asyncio.run(run_code_interpreter_demo())

# ## 2. File Search Tool
#
# The File Search Tool allows agents to search through vector stores and document collections to find relevant information.
#
# **Key Features:**
# - Search through vector stores
# - Retrieve relevant documents
# - Support for semantic search
# - Configurable result limits
#
# **Note:** This example requires a pre-configured vector store ID.
# File Search Tool Example


async def run_file_search_demo():
    # Note: You'll need to replace this with your actual vector store ID
    vector_store_id = "vs_67bf88953f748191be42b462090e53e7"

    agent = Agent(
        name="File searcher",
        instructions="You are a helpful agent.",
        tools=[
            FileSearchTool(
                max_num_results=3,
                vector_store_ids=[vector_store_id],
                include_search_results=True,
            )
        ],
    )

    with trace("File search example"):
        try:
            result = await Runner.run(agent, "Be concise, and tell me 1 sentence about Arrakis I might not know.")
            print(result.final_output)
            print("\n".join([str(out) for out in result.new_items]))
        except Exception as e:
            print(f"File search demo requires a valid vector store ID. Error: {e}")


# Run the demo
asyncio.run(run_file_search_demo())

# ## 3. Image Generation Tool
#
# The Image Generation Tool enables agents to create images from text descriptions using AI image generation models.
#
# **Key Features:**
# - Generate images from text prompts
# - Configurable quality settings
# - Support for various image styles
# - Automatic image saving and display
# Image Generation Tool Example


def open_file(path: str) -> None:
    if sys.platform.startswith("darwin"):
        subprocess.run(["open", path], check=False)  # macOS
    elif os.name == "nt":  # Windows
        os.startfile(path)  # type: ignore
    elif os.name == "posix":
        subprocess.run(["xdg-open", path], check=False)  # Linux/Unix
    else:
        print(f"Don't know how to open files on this platform: {sys.platform}")


async def run_image_generation_demo():
    agent = Agent(
        name="Image generator",
        instructions="You are a helpful agent.",
        tools=[
            ImageGenerationTool(
                tool_config={"type": "image_generation", "quality": "low"},
            )
        ],
    )

    with trace("Image generation example"):
        print("Generating image, this may take a while...")
        result = await Runner.run(agent, "Create an image of a frog eating a pizza, comic book style.")
        print(result.final_output)
        for item in result.new_items:
            if (
                item.type == "tool_call_item"
                and item.raw_item.type == "image_generation_call"
                and (img_result := item.raw_item.result)
            ):
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp.write(base64.b64decode(img_result))
                    temp_path = tmp.name

                # Open the image (optional - may not work in headless environments)
                print(f"Image saved to: {temp_path}")
                try:
                    open_file(temp_path)
                    print("Image opened successfully")
                except Exception as e:
                    print(f"Could not open image automatically (this is normal in headless environments): {e}")
                    print("You can manually open the image file if needed")


# Run the demo
asyncio.run(run_image_generation_demo())

# ## 4. Web Search Tool
#
# The Web Search Tool allows agents to search the internet for current information and real-time data.
#
# **Key Features:**
# - Search the web for current information
# - Location-aware search results
# - Real-time data access
# - Configurable search parameters
# Web Search Tool Example


async def run_web_search_demo():
    agent = Agent(
        name="Web searcher",
        instructions="You are a helpful agent.",
        tools=[WebSearchTool(user_location={"type": "approximate", "city": "New York"})],
    )

    with trace("Web search example"):
        result = await Runner.run(
            agent,
            "search the web for 'local sports news' and give me 1 interesting update in a sentence.",
        )
        print(result.final_output)
        # Example output: The New York Giants are reportedly pursuing quarterback Aaron Rodgers after his ...


# Run the demo
asyncio.run(run_web_search_demo())
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


# ## Conclusion
#
# Each tool extends agent capabilities and enables sophisticated automation. **AgentOps makes tool observability effortless** - simply import the library and all your tool interactions are automatically tracked, visualized, and analyzed. This enables you to:
#
# - Monitor tool performance across different use cases
# - Optimize costs by understanding tool usage patterns
# - Debug tool integration issues quickly
# - Scale your AI applications with confidence in tool reliability
#
# Visit [app.agentops.ai](https://app.agentops.ai) to explore your tool usage sessions and gain deeper insights into your AI application's tool interactions.
