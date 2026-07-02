# Astraflow Example
#
# This example demonstrates how to use Astraflow (UCloud / 优刻得 umodelverse) with AgentOps via the OpenAI Python client.
#
# Astraflow is an OpenAI-compatible AI model aggregation platform supporting 200+ models.
# Because it is OpenAI-compatible, AgentOps' built-in OpenAI instrumentation automatically
# tracks every Astraflow call once you point the OpenAI client at the Astraflow base_url.
#
# Endpoints:
#   - Global: https://api-us-ca.umodelverse.ai/v1   (env: ASTRAFLOW_API_KEY)
#   - China:  https://api.modelverse.cn/v1          (env: ASTRAFLOW_CN_API_KEY)
#
# First let's install the required packages
# %pip install -U openai
# %pip install -U agentops
# %pip install -U python-dotenv
from openai import OpenAI
import agentops
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "your_api_key_here")

# Initialize the AgentOps client
agentops.init(
    auto_start_session=False,
    trace_name="Astraflow Example",
    tags=["astraflow", "agentops-example"],
)
tracer = agentops.start_trace(
    trace_name="Astraflow Example", tags=["astraflow-example", "agentops-example"]
)

# Pick an Astraflow endpoint. Default to the global endpoint; switch to the China
# endpoint by setting ASTRAFLOW_CN_API_KEY instead of ASTRAFLOW_API_KEY.
if os.getenv("ASTRAFLOW_CN_API_KEY"):
    base_url = "https://api.modelverse.cn/v1"
    api_key = os.getenv("ASTRAFLOW_CN_API_KEY")
else:
    base_url = "https://api-us-ca.umodelverse.ai/v1"
    api_key = os.getenv("ASTRAFLOW_API_KEY", "your_astraflow_api_key_here")

# Initialize the OpenAI client pointed at Astraflow
client = OpenAI(base_url=base_url, api_key=api_key)

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Tell me a fun fact about observability for AI agents."},
    ],
)

print(response.choices[0].message.content)

agentops.end_trace(tracer, end_state="Success")

# Verify spans were recorded
print("\n" + "=" * 50)
print("Now let's verify that our LLM calls were tracked properly...")
try:
    agentops.validate_trace_spans(trace_context=tracer)
    print("\n✅ Success! All LLM spans were properly recorded in AgentOps.")
except agentops.ValidationError as e:
    print(f"\n❌ Error validating spans: {e}")
    raise
