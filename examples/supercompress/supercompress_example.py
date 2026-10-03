"""
# SuperCompress + AgentOps

Compress bulky agent context before the LLM call, then observe token/cost impact in AgentOps.

[SuperCompress](https://www.supercompress.dev) is query-aware context compression.
[AgentOps](https://agentops.ai) traces LLM spend and agent runs.

Pattern: bulky context → SuperCompress (keep ask intact) → OpenAI → AgentOps spans.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Next, we'll set our API keys. There are several ways to do this; this covers
# both env-file users and notebook paste. Remember not to commit real keys.
#
# [Get an AgentOps API key](https://app.agentops.ai/settings/projects)
# [Get a SuperCompress API key](https://www.supercompress.dev/dashboard) (optional for local compiler mode)

os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "your_api_key_here")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")
os.environ.setdefault("SUPERCOMPRESS_API_KEY", os.getenv("SUPERCOMPRESS_API_KEY", ""))

import agentops
from openai import OpenAI
from supercompress import compress_for_turn

BULKY_CONTEXT = """
# Agent dump (synthetic)

Root cause: null deref in checkout when cart.line_items is empty.
Fix hint: guard cart.line_items before mapping SKUs.
Passed unit tests for shipping calculator.
Unrelated filler about yesterday's standup and coffee preferences.
Noise: redis reconnect logs repeating 40 times.
Noise: webpack rebuild spam.
Noise: deprecated warning stack from leftover middleware.
GraphQL schema for ProductVariant is 800 lines of noise here.
Protobuf definitions for InventoryService (truncated).
Deno deploy logs from an unrelated service.
RFC8259 JSON grammar excerpts nobody asked for.
esbuild timing tables.
CRDT merge notes for a different ticket.
Wasm trap tables.
"""

USER_ASK = "Why does checkout crash on empty cart?"


def main():
    agentops.init(auto_start_session=False, trace_name="SuperCompress Example")
    tracer = agentops.start_trace(
        trace_name="SuperCompress Example",
        tags=["supercompress-example", "agentops-example", "token-savings"],
    )

    # Compress bulky context; never compress the user ask itself.
    result = compress_for_turn(
        context="",
        user_query=USER_ASK,
        context_blocks=[BULKY_CONTEXT],
        budget_ratio=0.35,
        # "compiler" = local query-aware fallback (no hosted key required).
        # Use mode="precision" + SUPERCOMPRESS_API_KEY for the hosted Neural Keep path.
        mode="compiler",
    )
    print(
        f"SuperCompress: {result.original_tokens} → {result.kept_tokens} tokens "
        f"({result.tokens_saved_pct}% saved, mode={result.mode})"
    )

    client = OpenAI()
    messages = [
        {"role": "system", "content": result.compressed_text},
        {"role": "user", "content": USER_ASK},
    ]
    response = client.chat.completions.create(model="gpt-4o-mini", messages=messages)
    print(response.choices[0].message.content)

    agentops.end_trace(tracer, end_state="Success")

    print("\n" + "=" * 50)
    print("Verifying AgentOps spans...")
    try:
        agentops.validate_trace_spans(trace_context=tracer)
        print("\n✅ Success! LLM spans recorded in AgentOps.")
    except agentops.ValidationError as e:
        print(f"\n❌ Error validating spans: {e}")
        raise


if __name__ == "__main__":
    main()
