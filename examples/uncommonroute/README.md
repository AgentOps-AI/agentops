# AgentOps + UncommonRoute: Track and Optimize LLM Costs

[AgentOps](https://github.com/AgentOps-AI/agentops) tracks what your agents spend. [UncommonRoute](https://github.com/CommonstackAI/UncommonRoute) cuts that spend by routing each request to the cheapest model that can handle it.

Together they close the loop: **observe → optimize → verify**.

## How it works

```
Your Agent → UncommonRoute (local proxy) → cheapest capable model
     ↓
AgentOps (traces every call, tracks cost per request)
```

UncommonRoute analyzes each request using three signals (metadata, embeddings, structural complexity) and routes it to the optimal model:

| Task complexity | Routed to | Example |
|----------------|-----------|---------|
| Trivial | nano model (~$0.0008) | "hello" |
| Simple | budget model (~$0.001) | "fix the typo on line 3" |
| Medium | mid-tier (~$0.03) | "refactor this function" |
| Complex | premium (~$0.05) | "design a distributed scheduler" |

**Result**: ~82% cost reduction with 93.4% task completion rate.

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize UncommonRoute (one-time setup)
uncommon-route init

# Start the local proxy
uncommon-route serve

# Set your AgentOps API key
export AGENTOPS_API_KEY="***"

# Run the example
python uncommonroute_cost_optimization.py
```

## What you'll see in the AgentOps dashboard

- Cost breakdown per LLM call
- Which model UncommonRoute selected for each task
- Total session cost (compare with always-premium routing)