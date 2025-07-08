# # IBM Watsonx AI Streaming with AgentOps
#
# This notebook demonstrates how to use IBM Watsonx AI for streaming text generation and streaming chat completion with AgentOps instrumentation.
# ## Setup
#
# First, let's import the necessary libraries and initialize AgentOps:
import agentops
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "your_api_key_here")

# Initialize AgentOps
agentops.init(trace_name="WatsonX Streaming Example", tags=["watsonx-streaming", "agentops-example"])
# ## Initialize IBM Watsonx AI Credentials
#
# To use IBM Watsonx AI, you need to set up your credentials and project ID.
# Initialize credentials - replace with your own API key
# Best practice: Store API keys in environment variables
# Ensure WATSONX_API_KEY is set in your .env file or environment
os.environ["WATSONX_API_KEY"] = os.getenv("WATSONX_API_KEY", "your_watsonx_api_key_here")

credentials = Credentials(
    url=os.getenv("WATSONX_URL", "https://eu-de.ml.cloud.ibm.com"),
    api_key=os.environ["WATSONX_API_KEY"],
)

# Project ID for your IBM Watsonx project
project_id = os.getenv("WATSONX_PROJECT_ID", "your-project-id-here")
# ## Initialize Models
#
# Let's initialize models for our streaming examples:
# Initialize text generation model
gen_model = ModelInference(model_id="google/flan-ul2", credentials=credentials, project_id=project_id)

# Initialize chat model
chat_model = ModelInference(
    model_id="meta-llama/llama-3-3-70b-instruct", credentials=credentials, project_id=project_id
)
# ## Streaming Text Generation
#
# Let's use IBM Watsonx AI to generate streaming text:
# Streaming text generation
prompt = "List 3 benefits of machine learning:"
stream_response = gen_model.generate_text_stream(prompt)

print("Streaming Response:")
full_stream_response = ""
for chunk in stream_response:
    if isinstance(chunk, str):
        print(chunk, end="", flush=True)
        full_stream_response += chunk
print("\\n\\nComplete Response:")
print(full_stream_response)
# ## Streaming Chat Completion
#
# Now, let's try streaming chat completion:
# Format messages for chat
chat_stream_messages = [
    {"role": "system", "content": "You are a concise assistant."},
    {"role": "user", "content": "Explain the concept of photosynthesis in one sentence."},
]

# Get streaming chat response
chat_stream_response_gen = chat_model.chat_stream(messages=chat_stream_messages)

print("Chat Stream Response:")
full_chat_stream_response = ""
for chunk in chat_stream_response_gen:
    try:
        # Check structure based on SDK docstring example
        if chunk and "choices" in chunk and chunk["choices"]:
            delta = chunk["choices"][0].get("delta", {})
            content_chunk = delta.get("content")
            if content_chunk:
                print(content_chunk, end="", flush=True)
                full_chat_stream_response += content_chunk
    except Exception as e:
        print(f"Error processing chat stream chunk: {e}, Chunk: {chunk}")

print("\\n\\nComplete Chat Response:")
print(full_chat_stream_response)
# ## Another Streaming Chat Example
#
# Let's try another example with a more complex query:
# New chat messages for streaming
chat_stream_messages = [
    {"role": "system", "content": "You are a helpful assistant that provides step-by-step explanations."},
    {"role": "user", "content": "Explain how to make a simple chocolate cake."},
]

# Get streaming chat response
chat_stream_response_gen = chat_model.chat_stream(messages=chat_stream_messages)

print("Chat Stream Response:")
full_chat_stream_response = ""
for chunk in chat_stream_response_gen:
    try:
        if chunk and "choices" in chunk and chunk["choices"]:
            delta = chunk["choices"][0].get("delta", {})
            content_chunk = delta.get("content")
            if content_chunk:
                print(content_chunk, end="", flush=True)
                full_chat_stream_response += content_chunk
    except Exception as e:
        print(f"Error processing chat stream chunk: {e}, Chunk: {chunk}")

print("\\n\\nComplete Chat Response:")
print(full_chat_stream_response)
# ## Clean Up
#
# Finally, let's close the persistent connection with the models:
# Close connections
gen_model.close_persistent_connection()
chat_model.close_persistent_connection()

# Let's check programmatically that spans were recorded in AgentOps
print("\n" + "=" * 50)
print("Now let's verify that our LLM calls were tracked properly...")
try:
    agentops.validate_trace_spans(trace_context=None)
    print("\n✅ Success! All LLM spans were properly recorded in AgentOps.")
except agentops.ValidationError as e:
    print(f"\n❌ Error validating spans: {e}")
    raise
