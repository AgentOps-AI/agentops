"""
LiteLLM Multi-Provider Example with AgentOps Integration

This example demonstrates how to use LiteLLM with multiple AI providers
(OpenAI, Anthropic, Cohere, etc.) while tracking all interactions
with AgentOps instrumentation.

Install required packages:
pip install litellm agentops

Set your API keys (set only the ones you have):
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"
export COHERE_API_KEY="your-cohere-key"
export AGENTOPS_API_KEY="your-agentops-key"
"""

import os
import agentops
import litellm

agentops.init()

tracer = agentops.start_trace("litellm-multi-provider-example")

print("🚀 Starting LiteLLM Multi-Provider Example with AgentOps")
print("=" * 60)

PROVIDERS = [
    {
        "name": "OpenAI",
        "models": ["gpt-4o-mini", "gpt-3.5-turbo"],
        "env_key": "OPENAI_API_KEY"
    },
    {
        "name": "Anthropic",
        "models": ["claude-3-haiku-20240307", "claude-3-sonnet-20240229"],
        "env_key": "ANTHROPIC_API_KEY"
    },
    {
        "name": "Cohere",
        "models": ["command-nightly", "command"],
        "env_key": "COHERE_API_KEY"
    }
]

def check_provider_availability():
    """Check which providers have API keys configured."""
    available_providers = []
    
    for provider in PROVIDERS:
        if os.getenv(provider["env_key"]):
            available_providers.append(provider)
            print(f"✅ {provider['name']}: API key found")
        else:
            print(f"⚠️  {provider['name']}: API key not found (skipping)")
    
    return available_providers

def test_basic_completion(model, provider_name):
    """Test basic completion with a specific model."""
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Respond concisely."},
        {"role": "user", "content": "What is the capital of France?"}
    ]
    
    try:
        print(f"🎯 Testing {provider_name} ({model})...")
        response = litellm.completion(
            model=model,
            messages=messages,
            max_tokens=50,
            temperature=0.3
        )
        
        content = response.choices[0].message.content
        tokens = response.usage.total_tokens if response.usage else "unknown"
        
        print(f"📝 Response: {content}")
        print(f"✅ {provider_name} successful! Tokens: {tokens}")
        return True
        
    except Exception as e:
        print(f"❌ {provider_name} failed: {e}")
        return False

def test_creative_writing(model, provider_name):
    """Test creative writing capabilities."""
    messages = [
        {"role": "user", "content": "Write a creative two-sentence story about a robot chef."}
    ]
    
    try:
        print(f"🎨 Creative writing test with {provider_name} ({model})...")
        response = litellm.completion(
            model=model,
            messages=messages,
            max_tokens=100,
            temperature=0.8
        )
        
        content = response.choices[0].message.content
        print(f"📖 Story: {content}")
        print(f"✅ Creative writing successful!")
        return True
        
    except Exception as e:
        print(f"❌ Creative writing failed: {e}")
        return False

def test_reasoning(model, provider_name):
    """Test reasoning capabilities."""
    messages = [
        {"role": "user", "content": "If a train travels 60 mph for 2.5 hours, how far does it go? Show your work."}
    ]
    
    try:
        print(f"🧠 Reasoning test with {provider_name} ({model})...")
        response = litellm.completion(
            model=model,
            messages=messages,
            max_tokens=150,
            temperature=0.1
        )
        
        content = response.choices[0].message.content
        print(f"🔢 Solution: {content}")
        print(f"✅ Reasoning test successful!")
        return True
        
    except Exception as e:
        print(f"❌ Reasoning test failed: {e}")
        return False

def compare_providers_on_task():
    """Compare how different providers handle the same task."""
    print("\n🏆 Provider Comparison: Same Task, Different Models")
    print("-" * 50)
    
    task_message = [
        {"role": "user", "content": "Explain machine learning in exactly one sentence."}
    ]
    
    results = []
    available_providers = check_provider_availability()
    
    for provider in available_providers:
        model = provider["models"][0]
        
        try:
            print(f"\n🔄 {provider['name']} ({model}):")
            response = litellm.completion(
                model=model,
                messages=task_message,
                max_tokens=100,
                temperature=0.5
            )
            
            content = response.choices[0].message.content
            tokens = response.usage.total_tokens if response.usage else 0
            
            print(f"📝 {content}")
            
            results.append({
                "provider": provider["name"],
                "model": model,
                "response": content,
                "tokens": tokens
            })
            
        except Exception as e:
            print(f"❌ {provider['name']} failed: {e}")
    
    print(f"\n📊 Comparison Summary:")
    for result in results:
        print(f"  • {result['provider']}: {result['tokens']} tokens")
    
    return results

def main():
    """Main function to run all provider tests."""
    try:
        print("\n🔍 Checking Provider Availability:")
        print("-" * 40)
        available_providers = check_provider_availability()
        
        if not available_providers:
            print("❌ No API keys found! Please set at least one provider's API key.")
            agentops.end_trace(tracer, end_state="Fail")
            return
        
        total_tests = 0
        successful_tests = 0
        
        for provider in available_providers:
            print(f"\n🧪 Testing {provider['name']} Provider")
            print("-" * 40)
            
            model = provider["models"][0]
            
            if test_basic_completion(model, provider["name"]):
                successful_tests += 1
            total_tests += 1
            
            if test_creative_writing(model, provider["name"]):
                successful_tests += 1
            total_tests += 1
            
            if test_reasoning(model, provider["name"]):
                successful_tests += 1
            total_tests += 1
        
        comparison_results = compare_providers_on_task()
        
        print("\n" + "=" * 60)
        print(f"🎉 Multi-Provider Testing Complete!")
        print(f"📊 Results: {successful_tests}/{total_tests} tests passed")
        print(f"🏆 Providers tested: {len(available_providers)}")
        print(f"🔄 Comparison responses: {len(comparison_results)}")
        
        agentops.end_trace(tracer, end_state="Success")
        
    except Exception as e:
        print(f"\n❌ Multi-provider testing failed: {e}")
        agentops.end_trace(tracer, end_state="Fail")
        raise

if __name__ == "__main__":
    main()
    
    print("\n" + "=" * 60)
    print("Now let's verify that our multi-provider LLM calls were tracked properly...")
    
    try:
        result = agentops.validate_trace_spans(trace_context=tracer)
        agentops.print_validation_summary(result)
    except agentops.ValidationError as e:
        print(f"❌ Error validating spans: {e}")
        raise
    
    print("\n✅ Success! All multi-provider LLM spans were properly recorded in AgentOps.")
