#!/usr/bin/env python3
"""
Test to verify provider-specific tracking behavior with LiteLLM callback + AgentOps.

User's claim: 
- OpenAI GPT-4o with LiteLLM callback: LLM events appear in AgentOps dashboard
- Anthropic Claude 3.5 Sonnet with LiteLLM callback: LLM events do NOT appear in dashboard

Key: Uses litellm.success_callback = ["agentops"] (not direct instrumentation)
"""

import os
import litellm
import agentops

def test_provider_with_callback(provider_name, model, test_message):
    """Test a provider with LiteLLM callback integration"""
    print(f"\n=== Testing {provider_name} with LiteLLM Callback ===")
    
    agentops.init(auto_start_session=False)
    tracer = agentops.start_trace(trace_name=f"{provider_name} LiteLLM Callback Test", tags=[f"{provider_name.lower()}-litellm-callback"])
    
    litellm.success_callback = ["agentops"]
    
    try:
        response = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": test_message}],
            max_tokens=30
        )
        
        content = response.choices[0].message.content
        print(f"✅ {provider_name} API call successful")
        print(f"   Response: {content}")
        
        agentops.end_trace(tracer, end_state="Success")
        
        print(f"✅ {provider_name} test completed successfully")
        print(f"   ^ Check AgentOps session URL above - {provider_name} LLM events should {'appear' if provider_name in ['OpenAI', 'Groq'] else 'be MISSING'}")
        
        return {
            "success": True,
            "response": content
        }
        
    except Exception as e:
        print(f"❌ {provider_name} Error: {e}")
        agentops.end_trace(tracer, end_state="Fail")
        
        return {
            "success": False,
            "error": str(e)
        }

def main():
    print("=== LiteLLM + AgentOps Callback Provider Comparison ===")
    print("Testing user's claim: OpenAI events appear, Anthropic events missing")
    print("Using: litellm.success_callback = ['agentops']\n")
    
    agentops_key = os.environ.get("AGENTOPS_API_KEY")
    groq_key = os.environ.get("GROQ_API_KEY") 
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    
    if not agentops_key:
        print("❌ AGENTOPS_API_KEY not found in environment")
        return
    
    missing_keys = []
    if not groq_key:
        missing_keys.append("GROQ_API_KEY")
    if not anthropic_key:
        missing_keys.append("ANTHROPIC_API_KEY")
    
    if missing_keys:
        print(f"❌ Missing API keys: {', '.join(missing_keys)}")
        return
    
    print("✅ All required API keys found")
    
    groq_result = test_provider_with_callback(
        "Groq",
        "groq/llama3-8b-8192",
        "Say 'Hello from Groq via LiteLLM callback!' and nothing else."
    )
    
    anthropic_result = test_provider_with_callback(
        "Anthropic", 
        "anthropic/claude-3-5-sonnet-20240620",
        "Say 'Hello from Anthropic via LiteLLM callback!' and nothing else."
    )
    
    print("\n" + "="*80)
    print("RESULTS SUMMARY")
    print("="*80)
    
    print(f"\n📊 Groq Test:")
    if groq_result["success"]:
        print(f"   ✅ API call successful")
        print(f"   🔍 Expected: LLM events SHOULD appear in dashboard trace")
    else:
        print(f"   ❌ API call failed: {groq_result['error']}")
    
    print(f"\n📊 Anthropic Test:")
    if anthropic_result["success"]:
        print(f"   ✅ API call successful") 
        print(f"   🔍 Expected: LLM events should be MISSING from dashboard trace")
    else:
        print(f"   ❌ API call failed: {anthropic_result['error']}")
    
    print("\n" + "="*80)
    print("VERIFICATION INSTRUCTIONS")
    print("="*80)
    print("1. Open the session URLs printed above in AgentOps dashboard")
    print("2. Check the trace for each session:")
    print("   - Groq session: Should show LLM events (like OpenAI)")
    print("   - Anthropic session: Should NOT show LLM events (user's bug report)")
    print("3. If this pattern is confirmed, the provider-specific bug is verified!")
    print("\n🐛 This would confirm: LiteLLM callback works for some providers but not Anthropic")

if __name__ == "__main__":
    main()
