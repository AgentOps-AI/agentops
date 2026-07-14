# DaoXE Chat Completions Example
#
# Demonstrates AgentOps monitoring for DaoXE via the OpenAI Python client.
# DaoXE is a multi-model, multi-protocol API gateway; this script uses the
# OpenAI Chat Completions path (base_url https://daoxe.com/v1).

# %pip install -U openai
# %pip install -U agentops
# %pip install -U python-dotenv

from openai import OpenAI
import agentops
import os
from dotenv import load_dotenv

load_dotenv()
os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "your_api_key_here")

agentops.init(
    auto_start_session=False,
    trace_name="DaoXE Chat Example",
    tags=["daoxe", "chat-completions", "agentops-example"],
)
tracer = agentops.start_trace(
    trace_name="DaoXE Chat Example",
    tags=["daoxe-example", "multi-protocol-gateway", "agentops-example"],
)

# Point the OpenAI client at DaoXE. Model IDs are account-scoped — set DAOXE_MODEL
# from authenticated /v1/models or your DaoXE pricing catalog.
client = OpenAI(
    base_url="https://daoxe.com/v1",
    api_key=os.getenv("DAOXE_API_KEY", "your_daoxe_api_key_here"),
)

response = client.chat.completions.create(
    model=os.getenv("DAOXE_MODEL", "YOUR_ACCOUNT_MODEL_ID"),
    messages=[
        {
            "role": "system",
            "content": "You are a concise assistant for API and observability tips.",
        },
        {
            "role": "user",
            "content": "Give one practical tip for monitoring multi-model LLM gateways.",
        },
    ],
)

print(response.choices[0].message.content)

agentops.end_trace(tracer, end_state="Success")

# Verify spans were recorded in AgentOps
print("\n" + "=" * 50)
print("Now let's verify that our LLM calls were tracked properly...")
try:
    agentops.validate_trace_spans(trace_context=tracer)
    print("\n✅ Success! All LLM spans were properly recorded in AgentOps.")
except agentops.ValidationError as e:
    print(f"\n❌ Error validating spans: {e}")
    raise
