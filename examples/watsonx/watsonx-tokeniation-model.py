# # IBM Watsonx AI Tokenization and Model Details with AgentOps
#
# This notebook demonstrates how to use IBM Watsonx AI for tokenization and retrieving model details with AgentOps instrumentation.
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
agentops.init(trace_name="WatsonX Tokenization Model Example", tags=["watsonx-tokenization", "agentops-example"])
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
# ## Initialize Model
#
# Let's initialize a model to work with:
# Initialize model
model = ModelInference(model_id="google/flan-ul2", credentials=credentials, project_id=project_id)
# ## Tokenization
#
# Let's use IBM Watsonx AI to tokenize text:
# Example text to tokenize
text_to_tokenize = "Hello, how are you today?"
tokens = model.tokenize(text_to_tokenize)
print(f"Tokenization Result:\\n{tokens}")
# ## Tokenizing Longer Text
#
# Let's try tokenizing a longer piece of text:
# Longer text to tokenize
longer_text = """Artificial intelligence (AI) is intelligence demonstrated by machines, 
as opposed to intelligence displayed by humans or other animals. 
Example tasks in which this is done include speech recognition, computer vision, 
translation between languages, and decision-making."""

tokens = model.tokenize(longer_text)
print(f"Tokens: {tokens}")
# ## Model Details
#
# Let's retrieve and display details about the model we're using:
# Get model details
model_details = model.get_details()
print(f"Model Details:\\n{model_details}")
# ## Exploring a Different Model
#
# Let's initialize a different model and get its details:
# Initialize another model
llama_model = ModelInference(
    model_id="meta-llama/llama-3-3-70b-instruct", credentials=credentials, project_id=project_id
)

# Get details of the new model
llama_model_details = llama_model.get_details()
print(f"Llama Model Details:\\n{llama_model_details}")

# Example text tokenization with the new model
example_text = "Let's see how this model tokenizes text."
llama_tokens = llama_model.tokenize(example_text)
print(f"\\nTokenization with Llama model:\\n{llama_tokens}")
# ## Comparing Tokenization Between Models
#
# Let's compare how different models tokenize the same text:
# Text to compare tokenization
comparison_text = "The quick brown fox jumps over the lazy dog."

# Tokenize with first model
flan_tokens = model.tokenize(comparison_text)
print(f"FLAN-UL2 tokens: {flan_tokens}")

# Tokenize with second model
llama_tokens = llama_model.tokenize(comparison_text)
print(f"\\nLlama tokens: {llama_tokens}")
# ## Clean Up
#
# Finally, let's close the persistent connection with the models:
# Close connections
model.close_persistent_connection()
llama_model.close_persistent_connection()

# Let's check programmatically that spans were recorded in AgentOps
print("\n" + "=" * 50)
print("Now let's verify that our LLM calls were tracked properly...")
try:
    agentops.validate_trace_spans(trace_context=None)
    print("\n✅ Success! All LLM spans were properly recorded in AgentOps.")
except agentops.ValidationError as e:
    print(f"\n❌ Error validating spans: {e}")
    raise
