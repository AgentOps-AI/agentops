#!/usr/bin/env python3
"""
Focused test to verify provider-specific tracking behavior with LiteLLM + AgentOps.

This script tests:
1. OpenAI GPT-4o with LiteLLM callback (user says this works)
2. Anthropic Claude 3.5 Sonnet with LiteLLM callback (user says this doesn't work)

Goal: Verify which LLM events actually appear in AgentOps dashboard traces.
"""

import os
import litellm
import agentops
from dotenv import load_dotenv

def test_openai_with_litellm():
    """Test OpenAI with LiteLLM callback - should show LLM events in dashboard"""
    print("\n=== Testing OpenAI GPT-4o with LiteLLM Callback ===")
    
    agentops.init(auto_start_session=False)
    session = agentops.start_session(tags=["openai-litellm-test"])
    
    litellm.success_callback = ["agentops"]
    
    try:
        response = litellm.completion(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Say 'Hello from OpenAI via LiteLLM!' and nothing else."}],
            max_tokens=20
        )
        
        content = response.choices[0].message.content
        print(f"✅ OpenAI Response: {content}")
        
        agentops.end_session(end_state="Success")
        print(f"📊 OpenAI Session URL: {session.session_url}")
        print("   ^ Check this URL - should show LLM event in trace")
        return session.session_url
        
    except Exception as e:
        print(f"❌ OpenAI Error: {e}")
        agentops.end_session(end_state="Fail")
        return None

def test_anthropic_with_litellm():
    """Test Anthropic with LiteLLM callback - user says LLM events don't appear"""
    print("\n=== Testing Anthropic Claude 3.5 Sonnet with LiteLLM Callback ===")
    
    agentops.init(auto_start_session=False)
    session = agentops.start_session(tags=["anthropic-litellm-test"])
    
    litellm.success_callback = ["agentops"]
    
    try:
        response = litellm.completion(
            model="anthropic/claude-3-5-sonnet-20240620",
            messages=[{"role": "user", "content": "Say 'Hello from Anthropic via LiteLLM!' and nothing else."}],
            max_tokens=20
        )
        
        content = response.choices[0].message.content
        print(f"✅ Anthropic Response: {content}")
        
        agentops.end_session(end_state="Success")
        print(f"📊 Anthropic Session URL: {session.session_url}")
        print("   ^ Check this URL - user says LLM events will be MISSING from trace")
        return session.session_url
        
    except Exception as e:
        print(f"❌ Anthropic Error: {e}")
        agentops.end_session(end_state="Fail")
        return None

def main():
    print("=== Provider-Specific LiteLLM + AgentOps Tracking Test ===")
    print("Testing user's claim: OpenAI works, Anthropic doesn't show LLM events")
    
    load_dotenv()
    
    agentops_key = os.environ.get("AGENTOPS_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    
    if not agentops_key:
        print("❌ AGENTOPS_API_KEY not found")
        return
    
    if not openai_key:
        print("❌ OPENAI_API_KEY not found")
        return
        
    if not anthropic_key:
        print("❌ ANTHROPIC_API_KEY not found")
        return
    
    print("✅ All API keys found")
    
    openai_session = test_openai_with_litellm()
    anthropic_session = test_anthropic_with_litellm()
    
    print("\n" + "="*80)
    print("VERIFICATION INSTRUCTIONS")
    print("="*80)
    
    if openai_session:
        print(f"1. Check OpenAI session: {openai_session}")
        print("   Expected: LLM event should appear in trace")
    
    if anthropic_session:
        print(f"2. Check Anthropic session: {anthropic_session}")
        print("   Expected: LLM event should be MISSING from trace (according to user)")
    
    print("\n🔍 Compare the two sessions:")
    print("   - If OpenAI shows LLM events but Anthropic doesn't,")
    print("     then the user's provider-specific bug is confirmed!")
    print("   - This would indicate a conflict between LiteLLM callback")
    print("     and AgentOps' existing Anthropic instrumentation")

if __name__ == "__main__":
    main()
