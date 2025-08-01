"""
LiteLLM Async Example with AgentOps Integration

This example demonstrates how to use LiteLLM's async capabilities
with AgentOps instrumentation to track concurrent LLM operations
and async streaming responses.

Install required packages:
pip install litellm agentops

Set your API keys:
export OPENAI_API_KEY="your-openai-key"
export AGENTOPS_API_KEY="your-agentops-key"
"""

import os
import asyncio
import agentops
import litellm

agentops.init()

tracer = agentops.start_trace("litellm-async-example")

print("🚀 Starting LiteLLM Async Example with AgentOps")
print("=" * 60)

async def async_completion_example():
    """Example of basic async completion."""
    print("\n⚡ Example 1: Basic Async Completion")
    print("-" * 40)
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain quantum computing in one paragraph."}
    ]
    
    try:
        print("🎯 Making async completion call...")
        response = await litellm.acompletion(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=150
        )
        
        content = response.choices[0].message.content
        print(f"📝 Response: {content}")
        print(f"✅ Async completion successful! Tokens used: {response.usage.total_tokens}")
        return response
        
    except Exception as e:
        print(f"❌ Error in async completion: {e}")
        raise

async def async_streaming_example():
    """Example of async streaming completion."""
    print("\n📡 Example 2: Async Streaming Completion")
    print("-" * 40)
    
    messages = [
        {"role": "user", "content": "Write a haiku about artificial intelligence."}
    ]
    
    try:
        print("🎯 Making async streaming completion call...")
        response = await litellm.acompletion(
            model="gpt-4o-mini",
            messages=messages,
            stream=True,
            max_tokens=100
        )
        
        print("📡 Async streaming response:")
        full_content = ""
        chunk_count = 0
        async for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                print(content, end="", flush=True)
                full_content += content
                chunk_count += 1
        
        print(f"\n✅ Async streaming completed! {chunk_count} chunks, {len(full_content)} characters")
        return full_content
        
    except Exception as e:
        print(f"❌ Error in async streaming: {e}")
        raise

async def concurrent_completions_example():
    """Example of concurrent async completions."""
    print("\n🔄 Example 3: Concurrent Async Completions")
    print("-" * 40)
    
    tasks = [
        {
            "name": "Math Problem",
            "messages": [{"role": "user", "content": "What is 15 * 23?"}]
        },
        {
            "name": "Creative Writing",
            "messages": [{"role": "user", "content": "Write a one-sentence story about a time traveler."}]
        },
        {
            "name": "Code Question",
            "messages": [{"role": "user", "content": "How do you reverse a string in Python?"}]
        }
    ]
    
    async def single_completion(task):
        """Run a single completion task."""
        try:
            print(f"🎯 Starting task: {task['name']}")
            response = await litellm.acompletion(
                model="gpt-4o-mini",
                messages=task["messages"],
                max_tokens=100
            )
            
            content = response.choices[0].message.content
            tokens = response.usage.total_tokens
            print(f"✅ {task['name']} completed ({tokens} tokens)")
            return {
                "task": task["name"],
                "response": content,
                "tokens": tokens
            }
            
        except Exception as e:
            print(f"❌ {task['name']} failed: {e}")
            return {"task": task["name"], "error": str(e)}
    
    try:
        print("🚀 Running 3 concurrent completions...")
        
        results = await asyncio.gather(*[single_completion(task) for task in tasks])
        
        print("\n📊 Concurrent Results:")
        total_tokens = 0
        for result in results:
            if "error" not in result:
                print(f"  • {result['task']}: {result['tokens']} tokens")
                total_tokens += result['tokens']
            else:
                print(f"  • {result['task']}: ERROR - {result['error']}")
        
        print(f"🎉 Concurrent completions finished! Total tokens: {total_tokens}")
        return results
        
    except Exception as e:
        print(f"❌ Error in concurrent completions: {e}")
        raise

async def async_function_calling_example():
    """Example of async function calling."""
    print("\n🛠️  Example 4: Async Function Calling")
    print("-" * 40)
    
    tools = [
        {
            "type": "function",
            "function": {
                "name": "calculate_tip",
                "description": "Calculate tip amount for a bill",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "bill_amount": {
                            "type": "number",
                            "description": "The total bill amount"
                        },
                        "tip_percentage": {
                            "type": "number",
                            "description": "The tip percentage (e.g., 15 for 15%)"
                        }
                    },
                    "required": ["bill_amount", "tip_percentage"]
                }
            }
        }
    ]
    
    messages = [
        {"role": "user", "content": "Calculate a 18% tip on a $45.50 bill."}
    ]
    
    try:
        print("🔧 Making async completion with function calling...")
        response = await litellm.acompletion(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools,
            max_tokens=150
        )
        
        if response.choices[0].message.tool_calls:
            print("🔧 Function call detected!")
            for tool_call in response.choices[0].message.tool_calls:
                print(f"  Function: {tool_call.function.name}")
                print(f"  Arguments: {tool_call.function.arguments}")
        else:
            print(f"📝 Response: {response.choices[0].message.content}")
        
        print(f"✅ Async function calling completed! Tokens: {response.usage.total_tokens}")
        return response
        
    except Exception as e:
        print(f"❌ Error in async function calling: {e}")
        raise

async def main():
    """Main async function to run all examples."""
    try:
        await async_completion_example()
        await async_streaming_example()
        await concurrent_completions_example()
        await async_function_calling_example()
        
        print("\n" + "=" * 60)
        print("🎉 All LiteLLM Async Examples completed successfully!")
        
        agentops.end_trace(tracer, end_state="Success")
        
    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        agentops.end_trace(tracer, end_state="Fail")
        raise

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Warning: OPENAI_API_KEY not set. Please set your API key.")
    
    asyncio.run(main())
    
    print("\n" + "=" * 60)
    print("Now let's verify that our async LLM calls were tracked properly...")
    
    try:
        result = agentops.validate_trace_spans(trace_context=tracer)
        agentops.print_validation_summary(result)
    except agentops.ValidationError as e:
        print(f"❌ Error validating spans: {e}")
        raise
    
    print("\n✅ Success! All async LLM spans were properly recorded in AgentOps.")
