# # IBM Watsonx AI Text Generation and Chat with AgentOps
#
# This notebook demonstrates how to use IBM Watsonx AI for basic text generation and chat completion tasks with AgentOps instrumentation.
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
agentops.init(trace_name="WatsonX Text Chat Example", tags=["watsonx-text-chat", "agentops-example"])
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
# ## Text Generation
#
# Let's use IBM Watsonx AI to generate text based on a prompt:
# Initialize text generation model
gen_model = ModelInference(model_id="google/flan-ul2", credentials=credentials, project_id=project_id)

# Generate text with a prompt
prompt = "Write a short poem about artificial intelligence:"
response = gen_model.generate_text(prompt)
print(f"Generated Text:\\n{response}")
# ## Chat Completion
#
# Now, let's use a different model for chat completion:
# Initialize chat model
chat_model = ModelInference(
    model_id="meta-llama/llama-3-3-70b-instruct", credentials=credentials, project_id=project_id
)

# Format messages for chat
messages = [
    {"role": "system", "content": "You are a helpful AI assistant."},
    {"role": "user", "content": "What are the three laws of robotics?"},
]

# Get chat response
chat_response = chat_model.chat(messages)
print(f"Chat Response:\\n{chat_response['choices'][0]['message']['content']}")
# ## Another Chat Example
#
# Let's try a different type of query:
# New chat messages
messages = [
    {"role": "system", "content": "You are an expert in machine learning."},
    {"role": "user", "content": "Explain the difference between supervised and unsupervised learning in simple terms."},
]

# Get chat response
chat_response = chat_model.chat(messages)
print(f"Chat Response:\\n{chat_response['choices'][0]['message']['content']}")
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
