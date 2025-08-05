"""
LiteLLM Streaming Example with AgentOps Integration

This example demonstrates how to use LiteLLM's streaming capabilities
with AgentOps instrumentation to track streaming responses and
time-to-first-token metrics.

Install required packages:
pip install litellm agentops

Set your API keys:
export OPENAI_API_KEY="your-openai-key"
export AGENTOPS_API_KEY="your-agentops-key"
"""

import os
import agentops
import litellm

agentops.init()

tracer = agentops.start_trace("litellm-streaming-example")

print("🚀 Starting LiteLLM Streaming Example with AgentOps")
print("=" * 60)

if not os.getenv("OPENAI_API_KEY"):
    print("⚠️  Warning: OPENAI_API_KEY not set. Please set your API key.")

print("\n📡 Example 1: Basic Streaming Completion")
print("-" * 40)

messages = [
    {"role": "system", "content": "You are a helpful assistant that writes creative stories."},
    {"role": "user", "content": "Write a short story about a robot learning to paint. Make it about 3 paragraphs."},
]

try:
    print("🎯 Making streaming completion call...")
    response = litellm.completion(model="gpt-4o-mini", messages=messages, stream=True, temperature=0.7, max_tokens=300)

    print("📝 Streaming response:")
    full_content = ""
    for chunk in response:
        if chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            print(content, end="", flush=True)
            full_content += content

    print(f"\n\n✅ Streaming completed! Total content length: {len(full_content)} characters")

except Exception as e:
    print(f"❌ Error in streaming completion: {e}")
    agentops.end_trace(tracer, end_state="Fail")
    raise

print("\n🌐 Example 2: Multi-Provider Streaming")
print("-" * 40)

providers_to_test = [
    ("gpt-3.5-turbo", "OpenAI"),
    ("claude-3-haiku-20240307", "Anthropic (if key available)"),
]

for model, provider_name in providers_to_test:
    try:
        print(f"\n🔄 Testing {provider_name} ({model})...")

        simple_messages = [{"role": "user", "content": "Count from 1 to 5 with a brief description of each number."}]

        response = litellm.completion(model=model, messages=simple_messages, stream=True, max_tokens=100)

        print(f"📡 {provider_name} streaming response:")
        chunk_count = 0
        for chunk in response:
            if chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
                chunk_count += 1

        print(f"\n✅ {provider_name} completed with {chunk_count} chunks")

    except Exception as e:
        print(f"⚠️  {provider_name} failed (likely missing API key): {e}")
        continue

print("\n🛠️  Example 3: Streaming with Function Calling")
print("-" * 40)

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "The city and state, e.g. San Francisco, CA"}
                },
                "required": ["location"],
            },
        },
    }
]

function_messages = [{"role": "user", "content": "What's the weather like in San Francisco?"}]

try:
    print("🔧 Making streaming completion with function calling...")
    response = litellm.completion(model="gpt-4o-mini", messages=function_messages, tools=tools, stream=True)

    print("📡 Function calling streaming response:")
    for chunk in response:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)
        elif hasattr(chunk.choices[0].delta, "tool_calls") and chunk.choices[0].delta.tool_calls:
            print(f"\n🔧 Tool call detected: {chunk.choices[0].delta.tool_calls}")

    print("\n✅ Function calling streaming completed!")

except Exception as e:
    print(f"❌ Error in function calling: {e}")

print("\n" + "=" * 60)
print("🎉 LiteLLM Streaming Example completed!")

agentops.end_trace(tracer, end_state="Success")

print("\n" + "=" * 60)
print("Now let's verify that our streaming LLM calls were tracked properly...")

try:
    result = agentops.validate_trace_spans(trace_context=tracer)
    agentops.print_validation_summary(result)
except agentops.ValidationError as e:
    print(f"❌ Error validating spans: {e}")
    raise

print("\n✅ Success! All streaming LLM spans were properly recorded in AgentOps.")
