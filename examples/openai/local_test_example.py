#!/usr/bin/env python3

import os
from openai import OpenAI
import agentops

os.environ['AGENTOPS_API_KEY'] = 'local-dev-api-key-placeholder'
os.environ['AGENTOPS_API_ENDPOINT'] = 'http://localhost:8000'
os.environ['AGENTOPS_APP_URL'] = 'http://localhost:3000'
os.environ['AGENTOPS_EXPORTER_ENDPOINT'] = 'http://localhost:4318/v1/traces'

os.environ['OPENAI_API_KEY'] = '${OPENAI_API_KEY}'

agentops.init(auto_start_session=True, trace_name="Local OpenAI Test", tags=["openai", "local-test"])
tracer = agentops.start_trace(
    trace_name="Local OpenAI Test", tags=["openai-local-test", "openai", "agentops-example"]
)

client = OpenAI()

print("🚀 Starting OpenAI example with local AgentOps...")
print("🖇 Trace URL will be shown in AgentOps output above")

system_prompt = """
You are a master storyteller, with the ability to create vivid and engaging stories.
You have experience in writing for children and adults alike.
You are given a prompt and you need to generate a story based on the prompt.
"""

user_prompt = "Write a very short story about a cyber-warrior trapped in the imperial time period."

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_prompt},
]

try:
    print("📝 Generating story with OpenAI...")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
    )
    
    print("\n📖 Generated Story:")
    print("=" * 50)
    print(response.choices[0].message.content)
    print("=" * 50)
    
    print("\n🔄 Testing streaming version...")
    stream = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        stream=True,
    )
    
    print("\n📖 Streaming Story:")
    print("=" * 50)
    for chunk in stream:
        if chunk.choices and len(chunk.choices) > 0:
            print(chunk.choices[0].delta.content or "", end="")
    print("\n" + "=" * 50)
    
    agentops.end_trace(tracer, end_state="Success")
    
    print("\n✅ OpenAI example completed successfully!")
    print("🖇 View trace at the URL shown in AgentOps output above")
    
    print("\n🔍 Validating trace spans...")
    try:
        result = agentops.validate_trace_spans(trace_context=tracer)
        agentops.print_validation_summary(result)
    except agentops.ValidationError as e:
        print(f"❌ Error validating spans: {e}")
        
except Exception as e:
    print(f"❌ Error during OpenAI example: {e}")
    agentops.end_trace(tracer, end_state="Error")
    raise
