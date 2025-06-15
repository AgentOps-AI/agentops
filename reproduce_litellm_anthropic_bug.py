#!/usr/bin/env python3
"""
Reproduction script for LiteLLM + AgentOps provider-specific tracking issue.

ISSUE: When using litellm.success_callback = ["agentops"], LLM events appear in 
AgentOps dashboard traces for OpenAI models but NOT for Anthropic models.

This script tests:
1. OpenAI GPT-4o with LiteLLM callback (should show LLM events in trace)
2. Anthropic Claude 3.5 Sonnet with LiteLLM callback (LLM events missing from trace)
3. Direct AgentOps instrumentation for both providers (should work for both)

Expected result: Dashboard trace will show LLM events for OpenAI but not Anthropic
when using LiteLLM callback, demonstrating the provider-specific bug.
"""

import os
import litellm
import agentops
from dotenv import load_dotenv

def test_provider_with_litellm_callback(provider_name, model, test_message, max_tokens=50):
    """Test a specific provider with LiteLLM + AgentOps callback integration"""
    print(f"\n=== Testing {provider_name} with LiteLLM Callback ===")
    
    try:
        messages = [{"role": "user", "content": test_message}]
        response = litellm.completion(
            model=model,
            messages=messages,
            max_tokens=max_tokens
        )
        
        content = response.choices[0].message.content
        print(f"✅ {provider_name} Response: {content}")
        print(f"📊 Check AgentOps dashboard to verify if LLM event appears in trace")
        return True
        
    except Exception as e:
        print(f"❌ {provider_name} Error: {e}")
        return False

def test_provider_direct_agentops(provider_name, client, test_message, max_tokens=50):
    """Test a provider with direct AgentOps instrumentation (no LiteLLM callback)"""
    print(f"\n=== Testing {provider_name} with Direct AgentOps Instrumentation ===")
    
    try:
        if provider_name == "OpenAI":
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": test_message}],
                max_tokens=max_tokens
            )
            content = response.choices[0].message.content
        elif provider_name == "Anthropic":
            response = client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": test_message}]
            )
            content = response.content[0].text
        else:
            print(f"❌ Unknown provider: {provider_name}")
            return False
            
        print(f"✅ {provider_name} Direct Response: {content}")
        print(f"📊 This should show LLM event in AgentOps trace (direct instrumentation)")
        return True
        
    except Exception as e:
        print(f"❌ {provider_name} Direct Error: {e}")
        return False

def main():
    print("=== LiteLLM + AgentOps Provider-Specific Bug Reproduction ===\n")
    print("TESTING: Dashboard trace visibility for LLM events with different providers")
    print("EXPECTED: OpenAI events appear in trace, Anthropic events missing from trace\n")
    
    load_dotenv()
    
    agentops_key = os.environ.get("AGENTOPS_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY") 
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    
    if openai_key:
        os.environ["OPENAI_API_KEY"] = openai_key
    if anthropic_key:
        os.environ["ANTHROPIC_API_KEY"] = anthropic_key
    
    if not agentops_key:
        print("❌ AGENTOPS_API_KEY not found in environment")
        return
    
    available_providers = []
    if openai_key:
        available_providers.append("OpenAI")
    if anthropic_key:
        available_providers.append("Anthropic")
    
    if not available_providers:
        print("❌ No provider API keys found (need OPENAI_API_KEY and/or ANTHROPIC_API_KEY)")
        return
        
    print(f"✅ API keys found for: {', '.join(available_providers)}")
    
    print("\n" + "="*60)
    print("PHASE 1: Testing LiteLLM Callback Integration")
    print("="*60)
    
    print("\n1. Initializing AgentOps...")
    agentops.init(auto_start_session=False)
    session = agentops.start_session(
        tags=["litellm-callback-test", "provider-comparison", "bug-reproduction"]
    )
    print(f"✅ AgentOps session started")
    
    print("\n2. Configuring LiteLLM with AgentOps callback...")
    litellm.success_callback = ["agentops"]
    print("✅ LiteLLM success_callback configured")
    
    callback_results = {}
    
    if openai_key:
        print("\n3a. Testing OpenAI GPT-4o with LiteLLM callback (should show in trace)...")
        callback_results["OpenAI"] = test_provider_with_litellm_callback(
            "OpenAI GPT-4o", 
            "gpt-4o", 
            "Say 'Hello from GPT-4o via LiteLLM!' and nothing else."
        )
    
    if anthropic_key:
        print("\n3b. Testing Anthropic Claude 3.5 Sonnet with LiteLLM callback (events missing from trace)...")
        callback_results["Anthropic"] = test_provider_with_litellm_callback(
            "Anthropic Claude 3.5 Sonnet", 
            "anthropic/claude-3-5-sonnet-20240620", 
            "Say 'Hello from Claude via LiteLLM!' and nothing else."
        )
    
    print("\n4. Testing multiple Anthropic calls to confirm missing events...")
    if anthropic_key:
        for i in range(2):
            success = test_provider_with_litellm_callback(
                f"Anthropic Call {i+1}", 
                "anthropic/claude-3-5-sonnet-20240620", 
                f"Test call #{i+1}. Respond with 'Call {i+1} received'.",
                max_tokens=20
            )
            if not success:
                break
    
    print("\n5. Ending LiteLLM callback test session...")
    agentops.end_session(end_state="Success")
    print(f"✅ LiteLLM callback session ended")
    
    print("\n" + "="*60)
    print("PHASE 2: Testing Direct AgentOps Instrumentation")
    print("="*60)
    
    print("\n6. Starting new session for direct instrumentation test...")
    litellm.success_callback = []
    direct_session = agentops.start_session(
        tags=["direct-instrumentation-test", "provider-comparison"]
    )
    print(f"✅ Direct instrumentation session started")
    
    direct_results = {}
    
    if openai_key:
        import openai
        openai_client = openai.OpenAI(api_key=openai_key)
        print("\n7a. Testing OpenAI with direct AgentOps instrumentation...")
        direct_results["OpenAI"] = test_provider_direct_agentops(
            "OpenAI", 
            openai_client, 
            "Say 'Hello from direct OpenAI!' and nothing else."
        )
    
    if anthropic_key:
        import anthropic
        anthropic_client = anthropic.Anthropic(api_key=anthropic_key)
        print("\n7b. Testing Anthropic with direct AgentOps instrumentation...")
        direct_results["Anthropic"] = test_provider_direct_agentops(
            "Anthropic", 
            anthropic_client, 
            "Say 'Hello from direct Anthropic!' and nothing else."
        )
    
    print("\n8. Ending direct instrumentation test session...")
    agentops.end_session(end_state="Success")
    print(f"✅ Direct instrumentation session ended")
    
    print("\n" + "="*80)
    print("FINAL RESULTS SUMMARY")
    print("="*80)
    
    print(f"\n📊 LiteLLM Callback Session Results:")
    print("Expected: OpenAI events visible, Anthropic events MISSING")
    for provider, success in callback_results.items():
        status = "✅ API CALL SUCCESS" if success else "❌ API CALL FAILED"
        print(f"  {provider} (LiteLLM callback): {status}")
    
    print(f"\n📊 Direct Instrumentation Session Results:")
    print("Expected: Both OpenAI and Anthropic events visible")
    for provider, success in direct_results.items():
        status = "✅ API CALL SUCCESS" if success else "❌ API CALL FAILED"
        print(f"  {provider} (Direct): {status}")
    
    print("\n" + "="*80)
    print("VERIFICATION INSTRUCTIONS")
    print("="*80)
    print("1. Open both AgentOps session URLs above in your browser")
    print("2. Check the LiteLLM Callback session:")
    print("   - OpenAI calls should show as LLM events in the trace")
    print("   - Anthropic calls should be MISSING from the trace (this is the bug)")
    print("3. Check the Direct Instrumentation session:")
    print("   - Both OpenAI and Anthropic should show as LLM events")
    print("4. If Anthropic events are missing only in the LiteLLM callback session,")
    print("   the provider-specific bug is confirmed!")
    print("\n🐛 BUG CONFIRMED if: LiteLLM callback session shows OpenAI events but no Anthropic events")

if __name__ == "__main__":
    main()
