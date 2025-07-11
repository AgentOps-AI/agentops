# ## Observing Responses API with AgentOps
#
# The Responses API is a new API that focuses on greater simplicity and greater expressivity when using our APIs. It is designed for multiple tools, multiple turns, and multiple modalities — as opposed to current APIs, which either have these features bolted onto an API designed primarily for text in and out (chat completions) or need a lot bootstrapping to perform simple actions (assistants api).
#
# Here I will show you a couple of new features that the Responses API has to offer and tie it all together at the end.
# `responses` solves for a number of user pain-points with our current set of APIs. During our time with the completions API, we found that folks wanted:
#
# - the ability to easily perform multi-turn model interactions in a single API call
# - to have access to our hosted tools (file_search, web_search, code_interpreter)
# - granular control over the context sent to the model
#
# As models start to develop longer running reasoning and thinking capabilities, users will want an async-friendly and stateful primitive. Response solves for this. With AgentOps, we can easily observe the Responses API in action.
# ## Basics
# By design, on the surface, the Responses API is very similar to the Completions API.
# # Install required dependencies
# %pip install agentops
# %pip install openai
# %pip install python-dotenv
from dotenv import load_dotenv
import os
import json
import agentops
from openai import OpenAI

load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")
os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "your_api_key_here")

agentops.init(
    auto_start_session=False, trace_name="OpenAI Web Search Example", tags=["openai", "web-search", "agentops-example"]
)
tracer = agentops.start_trace(
    trace_name="OpenAI Responses Example", tags=["openai-responses-example", "openai", "agentops-example"]
)
client = OpenAI()

response = client.responses.create(
    model="gpt-4o-mini",
    input="tell me a joke",
)

print(response.output[0].content[0].text)

# One key feature of the Response API is that it is stateful. This means that you do not have to manage the state of the conversation by yourself, the API will handle it for you. For example, you can retrieve the response at any time and it will include the full conversation history.
fetched_response = client.responses.retrieve(response_id=response.id)
print(fetched_response.output[0].content[0].text)

# You can continue the conversation by referring to the previous response.
response_two = client.responses.create(model="gpt-4o-mini", input="tell me another", previous_response_id=response.id)
print(response_two.output[0].content[0].text)

# You can of course manage the context yourself. But one benefit of OpenAI maintaining the context for you is that you can fork the response at any point and continue the conversation from that point.
response_two_forked = client.responses.create(
    model="gpt-4o-mini",
    input="I didn't like that joke, tell me another and tell me the difference between the two jokes",
    previous_response_id=response.id,  # Forking and continuing from the first response
)
output_text = response_two_forked.output[0].content[0].text
print(output_text)

# ## Hosted Tools
#
# Another benefit of the Responses API is that it adds support for hosted tools like `file_search` and `web_search`. Instead of manually calling the tools, simply pass in the tools and the API will decide which tool to use and use it.
#
# Here is an example of using the `web_search` tool to incorporate web search results into the response. You may already be familiar with how ChatGPT can search the web. You can now build similar experiences too! The web search tool uses the OpenAI Index, the one that powers the web search in ChatGPT, having being optimized for chat applications.
response = client.responses.create(
    model="gpt-4o",  # or another supported model
    input="What's the latest news about AI?",
    tools=[{"type": "web_search"}],
)
print(json.dumps(response.output, default=lambda o: o.__dict__, indent=2))

# ## Multimodal, Tool-augmented conversation
#
# The Responses API natively supports text, images, and audio modalities.
# Tying everything together, we can build a fully multimodal, tool-augmented interaction with one API call through the responses API.

# Display the image from the provided URL
url = "https://upload.wikimedia.org/wikipedia/commons/thumb/1/15/Cat_August_2010-4.jpg/2880px-Cat_August_2010-4.jpg"
# display(Image(url=url, width=400))

response_multimodal = client.responses.create(
    model="gpt-4o",
    input=[
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": "Come up with keywords related to the image, and search on the web using the search tool for any news related to the keywords"
                    ", summarize the findings and cite the sources.",
                },
                {
                    "type": "input_image",
                    "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/15/Cat_August_2010-4.jpg/2880px-Cat_August_2010-4.jpg",
                },
            ],
        }
    ],
    tools=[{"type": "web_search"}],
)

print(json.dumps(response_multimodal.__dict__, default=lambda o: o.__dict__, indent=4))
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


# In the above example, we were able to use the `web_search` tool to search the web for news related to the image in one API call instead of multiple round trips that would be required if we were using the Chat Completions API.
# With the responses API
# 🔥 a single API call can handle:
#
# ✅ Analyze a given image using a multimodal input.
#
# ✅ Perform web search via the `web_search` hosted tool
#
# ✅ Summarize the results.
#
# In contrast, With Chat Completions API would require multiple steps, each requiring a round trip to the API:
#
# 1️⃣ Upload image and get analysis → 1 request
#
# 2️⃣ Extract info, call external web search → manual step + tool execution
#
# 3️⃣ Re-submit tool results for summarization → another request
#
# We are very excited for you to try out the Responses API and see how it can simplify your code and make it easier to build complex, multimodal, tool-augmented interactions!
