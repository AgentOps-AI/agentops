"""
AgentOps + UncommonRoute: Track and Optimize LLM Costs

This example shows how to combine AgentOps (cost tracking) with
UncommonRoute (cost optimization) to get full visibility into your
LLM spending and automatically reduce it by ~82%.

Setup:
    pip install agentops openai
    pipx install uncommon-route
    uncommon-route init
    uncommon-route serve

Environment variables:
    AGENTOPS_API_KEY - your AgentOps API key
    OPENAI_API_KEY - your OpenAI API key (used by UncommonRoute upstream)
    ANTHROPIC_API_KEY - your Anthropic API key (optional, for more routing options)
"""

from openai import OpenAI
import agentops
import os
from dotenv import load_dotenv

load_dotenv()

os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "your_api_key_here")

# --- Initialize AgentOps FIRST (before any LLM calls) ---
agentops.init(
    auto_start_session=True,
    trace_name="UncommonRoute Cost Optimization",
    tags=["uncommonroute", "cost-optimization", "agentops-example"],
)

tracer = agentops.start_trace(
    trace_name="UncommonRoute Cost Optimization",
    tags=["uncommonroute", "cost-optimization"],
)

# --- Point the OpenAI client at UncommonRoute's local proxy ---
# UncommonRoute runs on localhost:8403 and is fully OpenAI-compatible.
# It analyzes each request and routes to the cheapest capable model.
client = OpenAI(
    base_url="http://localhost:8403/v1",
    api_key="not-needed",  # UR uses your provider keys configured during `uncommon-route init`
)

# --- Task 1: Simple greeting (routed to a cheap/fast model) ---
print("=== Task 1: Simple greeting ===")
response = client.chat.completions.create(
    model="uncommon-route/auto",
    messages=[{"role": "user", "content": "Say hello in three languages."}],
)
print(f"Response: {response.choices[0].message.content}\n")

# --- Task 2: Medium complexity (routed to a mid-tier model) ---
print("=== Task 2: Code explanation ===")
response = client.chat.completions.create(
    model="uncommon-route/auto",
    messages=[
        {
            "role": "user",
            "content": "Explain the difference between a mutex and a semaphore. Give a short code example in Python.",
        }
    ],
)
print(f"Response: {response.choices[0].message.content}\n")

# --- Task 3: Complex reasoning (routed to a premium model) ---
print("=== Task 3: Architecture design ===")
response = client.chat.completions.create(
    model="uncommon-route/auto",
    messages=[
        {
            "role": "system",
            "content": "You are a senior distributed systems architect.",
        },
        {
            "role": "user",
            "content": (
                "Design a rate limiter for a multi-region API gateway that handles "
                "100k requests/second. Consider consistency vs availability tradeoffs, "
                "clock skew, and burst handling. Provide a detailed architecture."
            ),
        },
    ],
)
print(f"Response: {response.choices[0].message.content}\n")

# --- End trace and show results ---
agentops.end_trace(tracer, end_state="Success")

print("=" * 60)
print("Check your AgentOps dashboard to see:")
print("  - Cost breakdown per request")
print("  - Which model UncommonRoute selected for each task")
print("  - Total spend vs. what it would have cost with a single premium model")
print("=" * 60)