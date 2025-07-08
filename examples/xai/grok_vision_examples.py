# XAI Vision Example
#
# This notebook demonstrates how to use XAI with AgentOps via the OpenAI python client.
#
# We are going to use the latest Grok model from XAI to create a program that will capture the text in an image and explain it. We will use AgentOps to track the program's performance.
# First let's install the required packages
# %pip install -U openai
# %pip install -U agentops
# Then import them
from openai import OpenAI
import agentops
import os
from dotenv import load_dotenv

# Next, we'll grab our API keys. You can use dotenv like below or however else you like to load environment variables
load_dotenv()
os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "your_api_key_here")
os.environ["XAI_API_KEY"] = os.getenv("XAI_API_KEY", "your_xai_api_key_here")

# Next we initialize the AgentOps client.
agentops.init(
    auto_start_session=False, trace_name="XAI Grok Vision Example", tags=["xai", "grok-vision", "agentops-example"]
)
tracer = agentops.start_trace(
    trace_name="XAI Grok Vision Example", tags=["xai-example", "grok-vision", "agentops-example"]
)

# And we are all set! Note the seesion url above. We will use it to track the program's performance.
#
# Let's initialize the OpenAI client with the XAI API key and base url.
client = OpenAI(
    base_url="https://api.x.ai/v1",
    api_key=os.getenv("XAI_API_KEY", "your_xai_api_key_here"),
)

# Next we will set the system and instruction prompts for the program.
SYSTEM_PROMPT = """You are an expert image analysis assistant. When presented with an image, carefully examine and describe its contents in detail. 

For this task, your goal is to:
1. Identify all key elements, objects, people, or text in the image
2. Provide a comprehensive description of what you observe
3. Explain the context or historical significance if applicable
4. Describe the image in a clear, objective, and informative manner

Please be precise, thorough, and focus on providing meaningful insights about the visual content."""

USER_PROMPT = [
    {"type": "text", "text": "Analyze the image and provide a detailed description of what you see."},
    {
        "type": "image_url",
        "image_url": {"url": "https://upload.wikimedia.org/wikipedia/commons/f/ff/First_Computer_Bug%2C_1945.jpg"},
    },
]

# Now we will use the OpenAI client to process the image and generate a response.
response = client.chat.completions.create(
    model="grok-2-vision-1212",
    messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": USER_PROMPT}],
    max_tokens=4096,
)

print(response.choices[0].message.content)

# Awesome! It returns a fascinating response explaining the image and also deciphering the text content. All of this can be tracked with AgentOps by going to the session url above.
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


# We end the session with a success state and a success reason. This is useful if you want to track the success or failure of the chatbot. In that case you can set the end state to failure and provide a reason. By default the session will have an indeterminate end state.
