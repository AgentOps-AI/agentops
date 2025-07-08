# Google Generative AI Example with AgentOps
#
# This notebook demonstrates how to use AgentOps with Google's Generative AI package for observing both synchronous and streaming text generation.
# # Instal necessary packages
# %pip install agentops
# %pip install google-genai
from google import genai
import agentops
from dotenv import load_dotenv
import os

load_dotenv()

os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "your_api_key_here")
os.environ["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY", "your_gemini_api_key_here")

# Initialize AgentOps and Gemini client
agentops.init(trace_name="Google Gemini Example", tags=["gemini-example", "agentops-example"])
client = genai.Client()

# Test synchronous generation
print("Testing synchronous generation:")
response = client.models.generate_content(model="gemini-1.5-flash", contents="What are the three laws of robotics?")
print(response.text)

# Test streaming generation
print("\nTesting streaming generation:")
response_stream = client.models.generate_content_stream(
    model="gemini-1.5-flash", contents="Explain the concept of machine learning in simple terms."
)

for chunk in response_stream:
    print(chunk.text, end="")
print()  # Add newline after streaming output

# Test another synchronous generation
print("\nTesting another synchronous generation:")
response = client.models.generate_content(
    model="gemini-1.5-flash", contents="What is the difference between supervised and unsupervised learning?"
)
print(response.text)

# Example of token counting
print("\nTesting token counting:")
token_response = client.models.count_tokens(
    model="gemini-1.5-flash", contents="This is a test sentence to count tokens."
)
print(f"Token count: {token_response.total_tokens}")

# Let's check programmatically that spans were recorded in AgentOps
print("\n" + "=" * 50)
print("Now let's verify that our LLM calls were tracked properly...")
try:
    agentops.validate_trace_spans(trace_context=None)
    print("\n✅ Success! All LLM spans were properly recorded in AgentOps.")
except agentops.ValidationError as e:
    print(f"\n❌ Error validating spans: {e}")
    raise
